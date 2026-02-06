users_db = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "profile_pic": "default.png"
    }
}

def add_user(username, password, role):

    if username in users_db:
        return False

    users_db[username] = {
        "password": password,
        "role": role,
        "profile_pic": "default.png"
    }

    return True


def validate_user(username, password):
    return username in users_db and users_db[username]["password"] == password


def get_user_role(username):

    if username not in users_db:
        return "viewer"

    return users_db[username]["role"]



def get_profile_pic(username):

    if username not in users_db:
        return "default.png"

    return users_db[username].get("profile_pic", "default.png")


def set_profile_pic(username, filename):
    users_db[username]["profile_pic"] = filename
