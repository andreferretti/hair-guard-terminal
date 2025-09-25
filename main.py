import cv2
import mediapipe as mp
import math
import time
import simpleaudio as sa
import os
import pyfiglet
import subprocess

# Load sound
alert_sound = sa.WaveObject.from_wave_file("alert.wav")

def send_mac_notification(title, message):
    """Send a native Mac notification using terminal-notifier"""
    try:
        # Try terminal-notifier first (more reliable)
        subprocess.run([
            "terminal-notifier", 
            "-title", title, 
            "-message", message,
            "-timeout", "3"
        ], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to osascript if terminal-notifier is not available
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=True)
        except subprocess.CalledProcessError:
            # If both fail, print to console as last resort
            print(f"NOTIFICATION: {title} - {message}")

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
                # Show text immediately when wrist is near temple
                cv2.putText(frame, "Wrist near temple!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if trigger_start_time == 0:
                    trigger_start_time = now
                elif now - trigger_start_time >= wait_before_beep_seconds:
                    if now - last_play_time > cooldown_seconds:
                        alert_sound.play()
                        send_mac_notification("Hair Twist Alert!", "Stop touching your hair!")
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