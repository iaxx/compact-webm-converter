from tkinter import Tk, filedialog, Label, Button, StringVar, LabelFrame
from tkinter.ttk import Progressbar
import os
import json
import subprocess
import threading
import re
from typing import Tuple


class WebmConverter:
    def __init__(self, root: Tk, ffmpeg_path: str, ffprobe_path: str, file_size_mb: int = 3):
        self.root = root
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.file_size_mb = file_size_mb
        self.file_path = None
        self.output_file = None
        self.duration_s = 0
        self.conversion_in_progress = False
        self.halve_resolution = False  # Flag to check if resolution should be halved
        self.target_framerate = 30  # Default target framerate
        self.remove_audio = False # Audio is not removed by default

        self.label = Label(self.root, text="Place the file here")
        self.label.pack()

        self.browse_button = Button(self.root, text="Browse", command=self.browse_file)
        self.browse_button.pack(pady=10)

        self.progress_var = StringVar()
        self.progress_var.set('0')
        self.progress_bar = Progressbar(self.root, length=400, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(pady=20)

        self.audio_frame = LabelFrame(self.root, text="Audio")
        self.audio_frame.pack(pady=5)

        self.audio_on_button = Button(self.audio_frame, text="On", command=self.set_audio_on)
        self.audio_on_button.pack(side="left", padx=5)

        self.audio_off_button = Button(self.audio_frame, text="Off", command=self.set_audio_off)
        self.audio_off_button.pack(side="left", padx=5)

        self.size_limit_frame = LabelFrame(self.root, text="File Size Limit (MB)")
        self.size_limit_frame.pack(pady=5)

        self.size_limit_3mb_button = Button(self.size_limit_frame, text="3 MB", command=self.set_size_limit_3mb)
        self.size_limit_3mb_button.pack(side="left", padx=5)

        self.size_limit_4mb_button = Button(self.size_limit_frame, text="4 MB", command=self.set_size_limit_4mb)
        self.size_limit_4mb_button.pack(side="left", padx=5)

        self.size_limit_8mb_button = Button(self.size_limit_frame, text="8 MB", command=self.set_size_limit_8mb)
        self.size_limit_8mb_button.pack(side="left", padx=5)

        self.resolution_frame = LabelFrame(self.root, text="Resolution")
        self.resolution_frame.pack(pady=5)

        self.half_res_button = Button(self.resolution_frame, text="Half res", command=self.set_half_resolution)
        self.half_res_button.pack(side="left", padx=5)

        self.full_res_button = Button(self.resolution_frame, text="Full res", command=self.set_full_resolution)
        self.full_res_button.pack(side="left", padx=5)

        self.framerate_frame = LabelFrame(self.root, text="Framerate")
        self.framerate_frame.pack(pady=5)

        self.framerate_30_button = Button(self.framerate_frame, text="30", command=self.set_framerate_30)
        self.framerate_30_button.pack(side="left", padx=5)

        self.framerate_60_button = Button(self.framerate_frame, text="60", command=self.set_framerate_60)
        self.framerate_60_button.pack(side="left", padx=5)

        self.go_button = Button(self.root, text="Start", command=self.start_conversion)
        self.go_button.pack(pady=10)

        self.message_label = Label(self.root, text="")
        self.message_label.pack()

    def get_video_duration(self, input_file: str) -> float:
        command = f'"{self.ffprobe_path}" -v quiet -print_format json -show_format -show_streams "{input_file}"'
        output = subprocess.check_output(command, shell=True, text=True)
        video_data = json.loads(output)
        duration_s = float(video_data['format']['duration'])
        return duration_s

    def get_video_resolution(self, input_file: str) -> Tuple[int, int]:
        command = f'"{self.ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height -of json "{input_file}"'
        output = subprocess.check_output(command, shell=True, text=True)
        video_data = json.loads(output)
        width = video_data['streams'][0]['width']
        height = video_data['streams'][0]['height']
        return width, height

    def calculate_bitrate(self, duration_s: float) -> float:
        file_size_kb = self.file_size_mb * 1024
        bitrate_k = file_size_kb * 8 / duration_s
        return bitrate_k

    def convert_to_webm(self, input_file: str, output_file: str, duration_s: float):
        # Disable the "Go" button during conversion
        self.go_button.config(state='disabled')

        # Update the message label
        self.message_label.config(text="Conversion in progress, please wait...")

        # Delete existing output file if it exists
        if os.path.exists(output_file):
            os.remove(output_file)

        try:
            width, height = self.get_video_resolution(input_file)
            if self.halve_resolution:
                width //= 2
                height //= 2
            scale_option = f"scale={width}:{height}"

            bitrate_k = self.calculate_bitrate(duration_s) * 0.96
            audio_option = "-an" if self.remove_audio else ""
            command = f'"{self.ffmpeg_path}" -i "{input_file}" -c:v vp9 -b:v {bitrate_k}k -vf "{scale_option},fps=fps={self.target_framerate}" {audio_option} -pass 1 -f webm NUL && "{self.ffmpeg_path}" -i "{input_file}" -c:v vp9 -b:v {bitrate_k}k -vf "{scale_option},fps=fps={self.target_framerate}" {audio_option} -pass 2 -f webm "{output_file}"'
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
                        self.progress_var.set(int((time_s / duration_s) * 100))

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
        self.go_button.config(state='normal')
        self.conversion_in_progress = False

        # Update the message label
        self.message_label.config(text="Conversion completed.")

    def browse_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=(("MP4 files", "*.mp4"), ("MKV files", "*.mkv"), ("All files", "*.*")))
        if self.file_path:
            self.output_file = self.file_path.rsplit('.', 1)[0] + '.webm'
            self.duration_s = self.get_video_duration(self.file_path)
            self.label.config(text="Selected file: " + os.path.basename(self.file_path))  # Display selected filename

    def start_conversion(self):
        if self.conversion_in_progress:
            return  # Skip if a conversion is already in progress

        self.conversion_in_progress = True
        threading.Thread(target=self.convert_to_webm, args=(self.file_path, self.output_file, self.duration_s)).start()

    def set_audio_on(self):
        self.remove_audio = False
        self.audio_on_button.config(state='disabled')
        self.audio_off_button.config(state='normal')

    def set_audio_off(self):
        self.remove_audio = True
        self.audio_off_button.config(state='disabled')
        self.audio_on_button.config(state='normal')

    def set_half_resolution(self):
        self.halve_resolution = True
        self.half_res_button.config(state='disabled')
        self.full_res_button.config(state='normal')

    def set_full_resolution(self):
        self.halve_resolution = False
        self.full_res_button.config(state='disabled')
        self.half_res_button.config(state='normal')

    def set_framerate_30(self):
        self.target_framerate = 30
        self.framerate_30_button.config(state='disabled')
        self.framerate_60_button.config(state='normal')

    def set_framerate_60(self):
        self.target_framerate = 60
        self.framerate_60_button.config(state='disabled')
        self.framerate_30_button.config(state='normal')

    def set_size_limit_3mb(self):
        self.file_size_mb = 3
        self.size_limit_3mb_button.config(state='disabled')
        self.size_limit_4mb_button.config(state='normal')
        self.size_limit_8mb_button.config(state='normal')

    def set_size_limit_4mb(self):
        self.file_size_mb = 4
        self.size_limit_4mb_button.config(state='disabled')
        self.size_limit_3mb_button.config(state='normal')
        self.size_limit_8mb_button.config(state='normal')

    def set_size_limit_8mb(self):
        self.file_size_mb = 8
        self.size_limit_8mb_button.config(state='disabled')
        self.size_limit_3mb_button.config(state='normal')
        self.size_limit_4mb_button.config(state='normal')

root = Tk()
root.title('3mb webm converter')
root.geometry('615x466')
root.minsize(615, 466)

ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe')
ffprobe_path = os.path.join(os.getcwd(), 'ffprobe.exe')

app = WebmConverter(root, ffmpeg_path, ffprobe_path)

root.mainloop()
