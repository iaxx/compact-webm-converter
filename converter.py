from tkinter import Tk, filedialog, Label, Button, StringVar
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

def get_video_duration(input_file):
    command = f'"{ffprobe_path}" -v quiet -print_format json -show_format -show_streams "{input_file}"'
    output = subprocess.check_output(command, shell=True, text=True)
    video_data = json.loads(output)
    duration_s = float(video_data['format']['duration'])
    return duration_s

def calculate_bitrate(file_size_mb, duration_s):
    file_size_kb = file_size_mb * 1024
    bitrate_k = file_size_kb * 8 / duration_s
    return bitrate_k

def convert_to_webm(input_file, output_file, duration_s):
    # Delete existing output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)

    try:
        bitrate_k = calculate_bitrate(file_size_mb, duration_s) * 0.96
        command = f'"{ffmpeg_path}" -i "{input_file}" -c:v libvpx-vp9 -b:v {bitrate_k}k -vf "fps=fps=30" -pass 1 -an -f webm NUL && "{ffmpeg_path}" -i "{input_file}" -c:v libvpx-vp9 -b:v {bitrate_k}k -vf "fps=fps=30" -pass 2 -an -f webm "{output_file}"'
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
    except KeyboardInterrupt:
        print("Conversion interrupted.")
    else:
        if process.returncode != 0:
            print(f'Error converting {input_file} to {output_file}')
        else:
            print(f'Successfully converted {input_file} to {output_file}')

def browse_file():
    global file_path, output_file, duration_s
    file_path = filedialog.askopenfilename(filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")))
    if file_path:
        output_file = file_path.rsplit('.', 1)[0] + '.webm'
        duration_s = get_video_duration(file_path)
        label.config(text="Selected file: " + os.path.basename(file_path))  # Display selected filename

def start_conversion():
    threading.Thread(target=convert_to_webm, args=(file_path, output_file, duration_s)).start()

root = Tk()
root.title('4chan webm converter')
root.geometry('460x232')
root.minsize(460, 232)

label = Label(root, text="Place the file here")
label.pack()

browse_button = Button(root, text="Browse", command=browse_file)
browse_button.pack(pady=10)

progress_var = StringVar()
progress_var.set('0')
progress_bar = Progressbar(root, length=400, mode='determinate', variable=progress_var)
progress_bar.pack(pady=20)

go_button = Button(root, text="Go", command=start_conversion)
go_button.pack(pady=10)

root.mainloop()
