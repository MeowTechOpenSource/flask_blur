import threading
from flask import Flask, redirect, url_for, render_template, request,session,flash,send_file, abort, jsonify
from werkzeug.utils import secure_filename
from operator import le
import face_recognition
import cv2
import time
import datetime
app = Flask(__name__)
app.secret_key="OOCheung"
jobrunning = False
percent = ""
remaining = ""
currfps = 0
def blurvideo(videoname):
    global remaining,currfps,jobrunning
    video_capture = cv2.VideoCapture(videoname)
    tracker_types = ['BOOSTING', 'MIL','KCF', 'TLD', 'MEDIANFLOW', 'GOTURN', 'MOSSE', 'CSRT']
    tracker_type = tracker_types[2]
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    tracker = ""
    if int(minor_ver) < 3:
        tracker = cv2.Tracker_create(tracker_type)
    else:
        tracker = cv2.TrackerKCF_create()
    # used to record the time when we processed last frame
    prev_frame_time = 0

    # used to record the time at which we processed current frame
    new_frame_time = 0
    # Read video
    #video = VideoFileClip("test.mp4")
    #audio = video.audio
    # Initialize some variables
    face_locations = []
    frames = []
    size = (0,0)
    p = 0
    ooldbbox = (287, 23, 86, 320)
    bbox = (287, 23, 86, 320)
    while True:
        p+=1
        # Grab a single frame of video
        ret, frame = video_capture.read()
        
        # Resize frame of video to 1/4 size for faster face detection processing
        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.75, fy=0.75)
        except:
            break
        if p == 1:
            height, width, layers = frame.shape
            size = (width,height)
            fps = int(video_capture.get(cv2.CAP_PROP_FPS))
            out = cv2.VideoWriter('project.MP4',cv2.VideoWriter_fourcc(*'mp4v'), fps, size,)
        
        # Find all the faces and face encodings in the current frame of video
        if p % 3 == 1:
            face_locations = face_recognition.face_locations(small_frame,)# model="cnn")

        # Display the results
        for top, right, bottom, left in face_locations:
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4/3
            right *= 4/3
            bottom *= 4/3
            left *= 4/3
            top = int(top)
            right = int(right)
            bottom = int(bottom)
            left = int(left)
            #print(top, bottom)
            #print(left,right)
            # Extract the region of the image that contains the face
            face_image = frame[top:bottom, left:right]
            #print(face_image)
            # Blur the face image
            face_image = cv2.GaussianBlur(face_image, (129, 129), 50)
            ooldbbox = bbox
            bbox = (left,top,bottom - top,right - left)
            #cv2.rectangle(frame,(bbox[0],bbox[1]),(bbox[0]+bbox[2],bbox[1]+bbox[3]),(0,0,255))
            if p == 1:
                ok = tracker.init(frame,bbox)
            else:
                try:
                    if bbox != ooldbbox:
                        if int(minor_ver) < 3:
                            tracker = cv2.Tracker_create(tracker_type)
                        else:
                            tracker = cv2.TrackerKCF_create()
                        ok = tracker.init(frame,bbox)
                    ok, bbox = tracker.update(frame)
                    #print(bbox)
                except Exception as e:
                    print(f'Error {e}')
            # Put the blurred face region back into the frame image
            frame[top:bottom, left:right] = face_image

        # Update tracker
        try:
            tracker.update(frame)
        except:
            pass
        try:
            ok
        except:
            ok = False
        # Draw bounding box
        if ok:
            # Tracking success
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            face_image = frame[p1[1]:p2[1], p1[0]:p2[0]]
            face_image = cv2.GaussianBlur(face_image, (129, 129), 50)
            #cv2.rectangle(frame, p1, p2, (255,0,0), 2, 1)
            frame[p1[1]:p2[1], p1[0]:p2[0]] = face_image
        # Display the resulting image
        #cv2.imshow('Video', frame)
        out.write(frame)
        total = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        ps = int((p / total) * 100)
        new_frame_time = time.time()
    
        # Calculating the fps
    
        # fps will be number of frame processed in given time frame
        # since their will be most of time error of 0.001 second
        # we will be subtracting it to get more accurate result
        fps2 = 1/(new_frame_time-prev_frame_time)
        prev_frame_time = new_frame_time
    
        # converting the fps into integer
        fps2 = int(fps2)
    
        # converting the fps to string so that we can display it on frame
        # by using putText function
        fps2 = str(fps2)
        if fps2 == "0":
            fps2 = 1
        remaining = (int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT)) - p) / int(fps2)
        global percent
        percent = str(ps)+"%"+f" [{str(p)}/{str(total)}]"
        remaining = str(datetime.timedelta(seconds=remaining))
        currfps = fps2
    jobrunning = False
@app.route('/info')
def current():
    global jobrunning
    if jobrunning:
        return jsonify({"status":"working","percent":percent,"fps":currfps,"remaining":remaining})
    else:
        return jsonify({"status":"completed"})
@app.route('/download_video.mp4')
def dlvideo():
    try:
        return send_file("project.MP4")
    except:
        return "Error, video not avalible."
@app.route('/',methods=['POST','GET'])
def uploadfile():
    global jobrunning
    if not jobrunning:
        if request.method == 'GET':
            return render_template("uploader.html")
        else:
            f = request.files['file']
            fname = secure_filename("video_"+f.filename)
            f.save(fname)
            jobrunning = True
            t1 = threading.Thread(target=blurvideo(fname))
            t1.daemon = True 
            t1.start()
            return redirect(url_for("status"))
    else:
        return "<h1>Sorry,Processing now</h1>"
@app.route('/status')
def status():
    return render_template("status.html")
if __name__ == "__main__":
	app.run(port=8888, debug=False)