videos_db = {}

def add_video(id, title, file, user, category):
    videos_db[id] = {
        "title": title,
        "filename": file,
        "uploader": user,
        "category": category,
        "views": 0
    }

def increment_views(id):
    videos_db[id]["views"] += 1
