import os, uuid
from flask import Flask, render_template, request, redirect, session, abort, send_from_directory
from werkzeug.utils import secure_filename

from data.users import add_user, validate_user, get_user_role, get_profile_pic, set_profile_pic
from data.videos import add_video, videos_db, increment_views
from data.logs import add_log

app = Flask(__name__)
app.secret_key = "snapstream_secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "videos")
PROFILE_FOLDER = os.path.join(BASE_DIR, "static", "profile_pics")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- CONTEXT PROCESSOR ----------------
@app.context_processor
def inject_user():

    if "user" in session:
        try:
            return dict(
                user=session["user"],
                role=session.get("role"),
                profile_pic=get_profile_pic(session["user"])
            )
        except:
            session.clear()

    return dict()


# ---------------- VIDEO SERVE ----------------
@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        if add_user(
            request.form["username"],
            request.form["password"],
            request.form["role"]
        ):
            return redirect("/login")

        return render_template("error.html", message="User exists")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        if validate_user(request.form["username"], request.form["password"]):

            session["user"] = request.form["username"]
            session["role"] = get_user_role(session["user"])

            return redirect("/dashboard")

        return render_template("error.html", message="Invalid login")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    # ⭐ SAFETY CHECK
    try:
        get_profile_pic(session["user"])
    except:
        session.clear()
        return redirect("/login")

    query = request.args.get("q")

    if query:
        filtered_videos = {
            id: v for id, v in videos_db.items()
            if query.lower() in v["title"].lower()
        }
    else:
        filtered_videos = videos_db

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session["role"],
        profile_pic=get_profile_pic(session["user"]),
        videos=filtered_videos,
        total_videos=len(filtered_videos),
        total_views=sum(v["views"] for v in filtered_videos.values())
    )


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    # ⭐ SAFETY CHECK
    try:
        get_profile_pic(session["user"])
    except:
        session.clear()
        return redirect("/login")

    return render_template(
        "profile.html",
        user=session["user"],
        role=session["role"],
        profile_pic=get_profile_pic(session["user"])
    )


# ---------------- PROFILE PIC UPLOAD ----------------
# @app.route("/upload_profile_pic", methods=["POST"])
# def upload_profile_pic():

#     if "user" not in session:
#         return redirect("/login")

#     file = request.files.get("profile_pic")

#     if file and file.filename != "":

#         ext = file.filename.split(".")[-1]
#         filename = f"{session['user']}.{ext}"

#         file.save(os.path.join(PROFILE_FOLDER, filename))

#         set_profile_pic(session["user"], filename)

#     return redirect("/profile")
@app.route("/upload_profile_pic", methods=["POST"])
def upload_profile_pic():

    if "user" not in session:
        return redirect("/login")

    file = request.files.get("profile_pic")

    if file and file.filename != "":

        username = session["user"]

        # ⭐ Remove old profile pictures
        for f in os.listdir(PROFILE_FOLDER):
            if f.startswith(username + "."):
                os.remove(os.path.join(PROFILE_FOLDER, f))

        # ⭐ Save new file with fixed naming
        ext = file.filename.split(".")[-1].lower()
        filename = f"{username}.{ext}"

        file.save(os.path.join(PROFILE_FOLDER, filename))

        set_profile_pic(username, filename)

    return redirect("/profile")



# ---------------- VIDEO UPLOAD ----------------
@app.route("/upload", methods=["GET","POST"])
def upload():

    if session.get("role") != "creator":
        abort(403)

    if request.method == "POST":

        file = request.files["video"]
        title = request.form["title"]

        vid = str(uuid.uuid4())
        name = secure_filename(vid + "_" + file.filename)

        file.save(os.path.join(app.config["UPLOAD_FOLDER"], name))

        add_video(vid, title, name, session["user"], "General")

        return redirect("/dashboard")

    return render_template("upload.html")


# ---------------- STREAM ----------------
@app.route("/stream/<vid>")
def stream(vid):

    if "user" not in session:
        return redirect("/login")

    if vid not in videos_db:
        abort(404)

    # ⭐ SAFETY CHECK
    try:
        get_profile_pic(session["user"])
    except:
        session.clear()
        return redirect("/login")

    increment_views(vid)
    add_log(session["user"], vid)

    return render_template(
        "stream.html",
        video=videos_db[vid],
        user=session["user"],
        role=session["role"],
        profile_pic=get_profile_pic(session["user"])
    )


# ---------------- ABOUT ----------------
@app.route("/about")
def about():

    if "user" not in session:
        return redirect("/login")

    return render_template("about.html")


# ---------------- SETTINGS ----------------
@app.route("/settings", methods=["GET","POST"])
def settings():

    if "user" not in session:
        return redirect("/login")

    msg = "Settings updated!" if request.method == "POST" else None

    return render_template(
        "settings.html",
        message=msg,
        user=session["user"],
        role=session["role"],
        profile_pic=get_profile_pic(session["user"])
    )


# ---------------- LOGOUT ----------------
# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("/")
@app.route("/logout")
def logout():

    session.pop("user", None)
    session.pop("role", None)
    session.clear()

    return redirect("/login")



if __name__ == "__main__":
    app.run(debug=True)
