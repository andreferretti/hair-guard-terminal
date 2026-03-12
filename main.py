import cv2
import mediapipe as mp
import math
import time
import simpleaudio as sa
import os
import pyfiglet
import subprocess
import numpy as np

# Load sound
alert_sound = sa.WaveObject.from_wave_file("alert.wav")

def send_mac_notification(title, message):
    # Send a native Mac notification using terminal-notifier
    subprocess.run([
        "terminal-notifier", 
        "-title", title, 
        "-message", message,
        "-timeout", "3"
    ], check=True, capture_output=True)

def distance(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

cap = cv2.VideoCapture(0)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

cooldown_seconds = 3
wait_before_beep_seconds = 0.69
last_play_time = 0
trigger_start_time = 0

with mp_pose.Pose(min_detection_confidence=0.8, min_tracking_confidence=0.8) as pose:
    while True:
        ret, frame = cap.read()
        
        # Clear all B.S. logs from mediapipe
        os.system('clear')
        print(pyfiglet.figlet_format("No hair twist!"))
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = frame.shape

            # Temples (use ears as proxies)
            left_temple = landmarks[7]
            right_temple = landmarks[8]

            left_temple_px = (int(left_temple.x * w), int(left_temple.y * h))
            right_temple_px = (int(right_temple.x * w), int(right_temple.y * h))
            cv2.circle(frame, left_temple_px, 10, (0, 0, 255), -1)   # red dot
            cv2.circle(frame, right_temple_px, 10, (0, 0, 255), -1)  # red dot

            # Wrists
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]

            left_wrist_px = (int(left_wrist.x * w), int(left_wrist.y * h))
            right_wrist_px = (int(right_wrist.x * w), int(right_wrist.y * h))
            cv2.circle(frame, left_wrist_px, 10, (0, 255, 255), -1)  # cyan
            cv2.circle(frame, right_wrist_px, 10, (0, 255, 0), -1)   # green

            # Lines to closest temples per wrist
            d_left_wrist_to_left_temple = distance(left_wrist, left_temple)
            d_left_wrist_to_right_temple = distance(left_wrist, right_temple)
            left_wrist_closest_temple_px = (
                left_temple_px if d_left_wrist_to_left_temple <= d_left_wrist_to_right_temple else right_temple_px
            )
            cv2.line(frame, left_wrist_closest_temple_px, left_wrist_px, (255, 0, 0), 2)

            d_right_wrist_to_left_temple = distance(right_wrist, left_temple)
            d_right_wrist_to_right_temple = distance(right_wrist, right_temple)
            right_wrist_closest_temple_px = (
                left_temple_px if d_right_wrist_to_left_temple <= d_right_wrist_to_right_temple else right_temple_px
            )
            cv2.line(frame, right_wrist_closest_temple_px, right_wrist_px, (255, 0, 0), 2)

            # Distance checks using closest temple per wrist
            d_left = min(d_left_wrist_to_left_temple, d_left_wrist_to_right_temple)
            d_right = min(d_right_wrist_to_left_temple, d_right_wrist_to_right_temple)

            trigger = False
            if d_right < 0.3:
                trigger = True
            elif d_left < 0.3:
                trigger = True

            now = time.time()

            if trigger:
                # Show warning banner centered on screen
                warn_text = "!! STOP TOUCHING !!"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 2
                thickness = 4
                text_size = cv2.getTextSize(warn_text, font, font_scale, thickness)[0]
                text_x = (w - text_size[0]) // 2
                text_y = int(h * 0.75)

                # Semi-transparent red background
                overlay = frame.copy()
                pad = 30
                cv2.rectangle(overlay,
                              (text_x - pad, text_y - text_size[1] - pad),
                              (text_x + text_size[0] + pad, text_y + pad),
                              (0, 0, 180), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

                # White text with black outline for readability
                cv2.putText(frame, warn_text, (text_x, text_y),
                            font, font_scale, (0, 0, 0), thickness + 2)
                cv2.putText(frame, warn_text, (text_x, text_y),
                            font, font_scale, (255, 255, 255), thickness)

                # Warning triangles on each side
                tri_y = text_y - text_size[1] // 2
                for tx in [text_x - pad - 40, text_x + text_size[0] + pad + 10]:
                    pts = np.array([(tx, tri_y + 15), (tx + 30, tri_y + 15), (tx + 15, tri_y - 15)])
                    cv2.fillPoly(frame, [pts], (0, 255, 255))
                    cv2.putText(frame, "!", (tx + 10, tri_y + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                if trigger_start_time == 0:
                    trigger_start_time = now
                elif now - trigger_start_time >= wait_before_beep_seconds:
                    if now - last_play_time > cooldown_seconds:
                        alert_sound.play()
                        send_mac_notification("Stop touching your hair!","You can do it.")
                        last_play_time = now
                        trigger_start_time = 0  # Reset to prevent repeated beeps
            else:
                trigger_start_time = 0
        
        cv2.imshow("Temple-based Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
os.system('clear')