// Upload validation (EXISTING CODE)
function validateUploadForm() {
    const title = document.getElementById("title").value;
    const file = document.getElementById("video").value;

    if (title.length < 3) {
        alert("Title must be at least 3 characters");
        return false;
    }
    if (!file) {
        alert("Select a video file");
        return false;
    }
    return true;
}


// ⭐ THEME TOGGLE FEATURE
function toggleTheme() {

    document.body.classList.toggle("light-theme");

    if(document.body.classList.contains("light-theme")) {
        localStorage.setItem("theme","light");
    }
    else {
        localStorage.setItem("theme","dark");
    }
}


// ⭐ LOAD SAVED THEME
window.onload = function(){

    const savedTheme = localStorage.getItem("theme");

    if(savedTheme === "light") {
        document.body.classList.add("light-theme");
    }

}
