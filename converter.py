from tkinter import Tk, filedialog, Label, Button, StringVar, LabelFrame
from tkinter.ttk import Progressbar
import os
import json
import subprocess
import threading
import re

# Path to ffmpeg and ffprobe executables
ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe')
ffprobe_path = os.path.join(os.getcwd(), 'ffprobe.exe')

# Desired output file size in MB
file_size_mb = 3

# Global variables
file_path = None
output_file = None
duration_s = 0
conversion_in_progress = False
halve_resolution = False  # Flag to check if resolution should be halved
target_framerate = 30  # Default target framerate

def get_video_duration(input_file):
    command = f'"{ffprobe_path}" -v quiet -print_format json -show_format -show_streams "{input_file}"'
    output = subprocess.check_output(command, shell=True, text=True)
    video_data = json.loads(output)
    duration_s = float(video_data['format']['duration'])
    return duration_s

def get_video_resolution(input_file):
    command = f'"{ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height -of json "{input_file}"'
    output = subprocess.check_output(command, shell=True, text=True)
    video_data = json.loads(output)
    width = video_data['streams'][0]['width']
    height = video_data['streams'][0]['height']
    return width, height

def calculate_bitrate(file_size_mb, duration_s):
    file_size_kb = file_size_mb * 1024
    bitrate_k = file_size_kb * 8 / duration_s
    return bitrate_k

def convert_to_webm(input_file, output_file, duration_s, halve_resolution, target_framerate):
    global conversion_in_progress

    # Disable the "Go" button during conversion
    go_button.config(state='disabled')

    # Update the message label
    message_label.config(text="Conversion in progress, please wait...")

    # Delete existing output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)

    try:
        width, height = get_video_resolution(input_file)
        if halve_resolution:
            width //= 2
            height //= 2
        scale_option = f"scale={width}:{height}"

        bitrate_k = calculate_bitrate(file_size_mb, duration_s) * 0.96
        command = f'"{ffmpeg_path}" -i "{input_file}" -c:v vp9 -b:v {bitrate_k}k -vf "{scale_option},fps=fps={target_framerate}" -pass 1 -an -f webm NUL && "{ffmpeg_path}" -i "{input_file}" -c:v vp9 -b:v {bitrate_k}k -vf "{scale_option},fps=fps={target_framerate}" -pass 2 -an -f webm "{output_file}"'
        process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
        regex = re.compile(r'time=(\d+:\d+:\d+.\d+)')
        while True:
            line = process.stderr.readline()
            if line == '' and process.poll() is not None:
                break
            if line:
                matches = regex.findall(line)
                if matches:
                    time_str = matches[0]
                    h, m, s = map(float, time_str.split(':'))
                    time_s = h * 3600 + m * 60 + s
                    progress_var.set(int((time_s / duration_s) * 100))

        # Wait for the process to terminate
        process.communicate()

    except KeyboardInterrupt:
        print("Conversion interrupted.")
    else:
        if process.returncode != 0:
            print(f'Error converting {input_file} to {output_file}')
        else:
            print(f'Successfully converted {input_file} to {output_file}')

    # Enable the "Go" button after conversion is finished
    go_button.config(state='normal')
    conversion_in_progress = False

    # Update the message label
    message_label.config(text="Conversion completed.")


    # Enable the "Go" button after conversion is finished
    go_button.config(state='normal')
    conversion_in_progress = False

    # Update the message label
    message_label.config(text="Conversion completed.")

def browse_file():
    global file_path, output_file, duration_s
    file_path = filedialog.askopenfilename(filetypes=(("MP4 files", "*.mp4"), ("MKV files", "*.mkv"), ("All files", "*.*")))
    if file_path:
        output_file = file_path.rsplit('.', 1)[0] + '.webm'
        duration_s = get_video_duration(file_path)
        label.config(text="Selected file: " + os.path.basename(file_path))  # Display selected filename

def start_conversion():
    global conversion_in_progress, halve_resolution, target_framerate

    if conversion_in_progress:
        return  # Skip if a conversion is already in progress

    conversion_in_progress = True
    threading.Thread(target=convert_to_webm, args=(file_path, output_file, duration_s, halve_resolution, target_framerate)).start()

def set_half_resolution():
    global halve_resolution
    halve_resolution = True
    half_res_button.config(state='disabled')
    full_res_button.config(state='normal')

def set_full_resolution():
    global halve_resolution
    halve_resolution = False
    full_res_button.config(state='disabled')
    half_res_button.config(state='normal')

def set_framerate_30():
    global target_framerate
    target_framerate = 30
    framerate_30_button.config(state='disabled')
    framerate_60_button.config(state='normal')

def set_framerate_60():
    global target_framerate
    target_framerate = 60
    framerate_60_button.config(state='disabled')
    framerate_30_button.config(state='normal')

root = Tk()
root.title('3mb webm converter')
root.geometry('490x340')
root.minsize(490, 340)

label = Label(root, text="Place the file here")
label.pack()

browse_button = Button(root, text="Browse", command=browse_file)
browse_button.pack(pady=10)

progress_var = StringVar()
progress_var.set('0')
progress_bar = Progressbar(root, length=400, mode='determinate', variable=progress_var)
progress_bar.pack(pady=20)

resolution_frame = LabelFrame(root, text="Resolution")
resolution_frame.pack(pady=5)

half_res_button = Button(resolution_frame, text="Half res", command=set_half_resolution)
half_res_button.pack(side="left", padx=5)

full_res_button = Button(resolution_frame, text="Full res", command=set_full_resolution)
full_res_button.pack(side="left", padx=5)

framerate_frame = LabelFrame(root, text="Framerate")
framerate_frame.pack(pady=5)

framerate_30_button = Button(framerate_frame, text="30", command=set_framerate_30)
framerate_30_button.pack(side="left", padx=5)

framerate_60_button = Button(framerate_frame, text="60", command=set_framerate_60)
framerate_60_button.pack(side="left", padx=5)

go_button = Button(root, text="Start", command=start_conversion)
go_button.pack(pady=10)

message_label = Label(root, text="")
message_label.pack()

root.mainloop()
