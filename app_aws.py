import os, uuid
from flask import Flask, render_template, request, redirect, session, abort, send_from_directory
from werkzeug.utils import secure_filename

import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = "snapstream_secret"

# -------- AWS CONFIG --------
REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

users_table = dynamodb.Table("Users")
videos_table = dynamodb.Table("Videos")
logs_table = dynamodb.Table("Logs")

SNS_TOPIC_ARN = "YOUR_SNS_TOPIC_ARN"


# -------- LOCAL STORAGE --------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "videos")
PROFILE_FOLDER = os.path.join(BASE_DIR, "static", "profile_pics")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -------- SNS HELPER --------
def notify(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print(e)


# -------- VIDEO SERVE --------
@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# -------- HOME --------
@app.route("/")
def home():
    return render_template("index.html")


# -------- REGISTER --------
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        res = users_table.get_item(Key={"username": username})

        if "Item" in res:
            return render_template("error.html", message="User exists")

        users_table.put_item(Item={
            "username": username,
            "password": password,
            "role": role,
            "profile_pic": "default.png"
        })

        notify("New User", f"{username} registered")

        return redirect("/login")

    return render_template("register.html")


# -------- LOGIN --------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        res = users_table.get_item(Key={"username": username})

        if "Item" in res and res["Item"]["password"] == password:

            session["user"] = username
            session["role"] = res["Item"]["role"]

            notify("Login", f"{username} logged in")

            return redirect("/dashboard")

        return render_template("error.html", message="Invalid login")

    return render_template("login.html")


# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    res = videos_table.scan()
    videos = res.get("Items", [])

    return render_template(
        "dashboard.html",
        videos={v["video_id"]: v for v in videos},
        total_videos=len(videos),
        total_views=sum(v.get("views",0) for v in videos)
    )


# -------- PROFILE PIC UPLOAD --------
@app.route("/upload_profile_pic", methods=["POST"])
def upload_profile_pic():

    if "user" not in session:
        return redirect("/login")

    file = request.files.get("profile_pic")

    if file:

        username = session["user"]
        ext = file.filename.split(".")[-1]
        filename = f"{username}.{ext}"

        file.save(os.path.join(PROFILE_FOLDER, filename))

        users_table.update_item(
            Key={"username": username},
            UpdateExpression="set profile_pic=:p",
            ExpressionAttributeValues={":p": filename}
        )

        notify("Profile Updated", f"{username} changed profile picture")

    return redirect("/profile")


# -------- PROFILE --------
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    res = users_table.get_item(Key={"username": session["user"]})

    return render_template(
        "profile.html",
        profile_pic=res["Item"]["profile_pic"]
    )


# -------- VIDEO UPLOAD --------
@app.route("/upload", methods=["GET","POST"])
def upload():

    if session.get("role") != "creator":
        abort(403)

    if request.method == "POST":

        file = request.files["video"]
        title = request.form["title"]

        vid = str(uuid.uuid4())
        filename = secure_filename(vid + "_" + file.filename)

        file.save(os.path.join(UPLOAD_FOLDER, filename))

        videos_table.put_item(Item={
            "video_id": vid,
            "title": title,
            "filename": filename,
            "uploader": session["user"],
            "views": 0,
            "category": "General"
        })

        notify("Video Upload", f"{session['user']} uploaded {title}")

        return redirect("/dashboard")

    return render_template("upload.html")


# -------- STREAM --------
@app.route("/stream/<vid>")
def stream(vid):

    if "user" not in session:
        return redirect("/login")

    res = videos_table.get_item(Key={"video_id": vid})

    video = res["Item"]

    videos_table.update_item(
        Key={"video_id": vid},
        UpdateExpression="set views = views + :v",
        ExpressionAttributeValues={":v": 1}
    )

    logs_table.put_item(Item={
        "log_id": str(uuid.uuid4()),
        "username": session["user"],
        "video_id": vid
    })

    return render_template("stream.html", video=video)


# -------- ABOUT --------
@app.route("/about")
def about():
    return render_template("about.html")


# -------- SETTINGS --------
@app.route("/settings")
def settings():
    return render_template("settings.html")


# -------- LOGOUT --------
@app.route("/logout")
def logout():

    notify("Logout", f"{session.get('user')} logged out")

    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
