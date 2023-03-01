
def extract_video_time(driver):
    t = driver.execute_script("""
    const root = document.getElementById('video-container');
    const vueInstance = root.__vue__;
    return vueInstance.video.currentTime;
    """)
    return max(t, 0)

def is_paused(driver):
    b = driver.execute_script("""
    const root = document.getElementById('video-container');
    const vueInstance = root.__vue__;
    return vueInstance.video.paused;
    """)
    return b


def is_annotating(driver):
    get_url = driver.current_url
    return 'annotations' in get_url

def image_or_video(driver):
    get_url = driver.current_url
    if 'image' in get_url:
        return 'image'
    elif 'videos' in get_url:
        return 'video'
    return None

def get_video_filename(driver):
    name_box = driver.find_element("id", "video-annotations-navbar")
    return name_box.find_element("tag name", "strong").text

def get_image_filename(driver):
    name_box = driver.find_element("id", "annotations-navbar")
    return name_box.find_element("tag name", "strong").text