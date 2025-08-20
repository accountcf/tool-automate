from moviepy.editor import *
clips = [VideoFileClip(f"clips/{i}.mp4").subclip(0, 7.5)
         for i in range(segments)]
audios = [AudioFileClip(f"output/{i:02d}.mp3") for i in range(segments)]
final = concatenate_videoclips(clips).set_audio(concatenate_audioclips(audios))
final.write_videofile("pov_tiktok.mp4", fps=30, audio_codec="aac")
