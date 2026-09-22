"""Bundled original BGM library: build five tracks or choose/mix a soundtrack."""
import argparse
import json
import math
import random
import subprocess
import wave
from pathlib import Path
import numpy as np

LIBRARY = Path(__file__).resolve().parent.parent / 'assets' / 'bgm'

def catalog():
    return json.loads((LIBRARY / 'catalog.json').read_text(encoding='utf-8'))['tracks']

def choose_track(track_id='random', previous=None):
    tracks = catalog()
    if track_id == 'random':
        choices = [t for t in tracks if t['id'] != previous]
        return random.SystemRandom().choice(choices or tracks)
    for track in tracks:
        if track['id'] == track_id:
            return track
    raise ValueError('Unknown bgm_id: ' + str(track_id))

def write_wav(path, audio, rate):
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes((np.clip(audio, -.98, .98) * 32767).astype('<i2').tobytes())

def build_library():
    rate, seconds = 22050, 24
    for track in catalog():
        audio = np.zeros(rate * seconds)
        beat = 60 / track['bpm']
        rng = np.random.default_rng(track['bpm'])
        def tone(start, midi, duration, gain, voice):
            offset = round(start * rate)
            count = min(round(duration * rate), len(audio) - offset)
            if count <= 0: return
            t = np.arange(count) / rate
            hz = 440 * 2 ** ((midi - 69) / 12)
            phase = 2 * np.pi * hz * t
            if voice == 'marimba':
                signal = np.sin(phase) + .32 * np.sin(phase * 4) * np.exp(-t * 18)
                decay = 7
            elif voice == 'bell':
                signal = np.sin(phase) + .23 * np.sin(phase * 2.76) * np.exp(-t * 5)
                decay = 4
            elif voice == 'keys':
                signal = np.sin(phase) + .27 * np.sin(phase * 2) + .10 * np.sin(phase * 3)
                decay = 2.5
            elif voice == 'round':
                signal = np.sin(phase) + .15 * np.sin(phase * 3)
                decay = 4.5
            else:
                signal = np.sin(phase) + .33 * np.sin(phase * 2) + .12 * np.sin(phase * 4)
                decay = 5.5
            envelope = (1 - np.exp(-t * 140)) * np.exp(-t * decay) * np.clip((duration - t) / .025, 0, 1)
            audio[offset:offset+count] += gain * signal * envelope
        step = beat * (.75 if track['timbre'] == 'keys' else .5)
        for i, start in enumerate(np.arange(0, seconds, step)):
            tone(start, track['notes'][i % len(track['notes'])], step * 1.7, .31, track['timbre'])
        for i, start in enumerate(np.arange(0, seconds, beat)):
            chord = track['chords'][(i // 4) % 4]
            tone(start, chord[0], beat * .85, .22, 'round')
            if i % 2 == 0:
                for j, midi in enumerate(chord): tone(start + .04*j, midi + 12, beat * 1.7, .055, 'keys')
            if track['timbre'] != 'keys':
                offset = round((start + beat*.5) * rate)
                n = min(round(.06*rate), len(audio)-offset)
                if n > 0:
                    audio[offset:offset+n] += .035 * rng.normal(size=n) * np.exp(-np.arange(n)/rate*80)
        fade = np.minimum(1, np.arange(len(audio))/rate/.04) * np.minimum(1, (len(audio)-np.arange(len(audio)))/rate/.3)
        audio *= fade
        audio *= .85 / max(np.max(np.abs(audio)), 1e-9)
        write_wav(LIBRARY / track['file'], audio, rate)
        print(track['id'])

def soundtrack(ffmpeg, cfg, duration, guess, work, rate=44100):
    track = choose_track(cfg.get('bgm_id', 'random'), cfg.get('previous_bgm_id'))
    target = cfg.get('bgm_lufs', -18)
    if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(target) or not -24 <= target <= -12:
        raise ValueError('bgm_lufs must be a finite number between -24 and -12')
    source = LIBRARY / track['file']
    if not source.is_file(): raise FileNotFoundError('Missing bundled BGM: ' + str(source))
    # Normalize music alone so timer effects cannot determine the music loudness.
    command = [ffmpeg,'-v','error','-stream_loop','-1','-i',str(source),'-t',str(duration),'-af',f'loudnorm=I={target}:TP=-3:LRA=7,afade=t=in:d=0.15,afade=t=out:st={duration-.7}:d=0.7','-ar',str(rate),'-ac','1','-f','f32le','pipe:1']
    result = subprocess.run(command, capture_output=True, check=True, timeout=60)
    audio = np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)
    audio = np.pad(audio, (0, max(0,rate*duration-len(audio))))[:rate*duration]
    def cue(start, freq, seconds, gain):
        at=round(start*rate); n=min(round(seconds*rate),len(audio)-at)
        t=np.arange(n)/rate
        audio[at:at+n] += gain*np.sin(2*np.pi*freq*t)*(1-np.exp(-t*150))*np.exp(-t*15)*np.clip((seconds-t)/.02,0,1)
    for second in range(1,guess): cue(second,1046.5,.12,.065)
    for i,freq in enumerate([523.25,659.25,783.99,1046.5]): cue(guess+i*.12,freq,.7,.09)
    peak=float(np.max(np.abs(audio)))
    if peak > .84: audio *= .84/peak
    write_wav(work/'music.wav', audio, rate)
    return audio, {'bgm_id':track['id'],'bgm_name':track['name'],'bgm_target_lufs':target,'bgm_selection':cfg.get('bgm_id','random'),'audio_rms_dbfs':float(20*np.log10(max(np.sqrt(np.mean(audio**2)),1e-12)))}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--pick',action='store_true')
    parser.add_argument('--previous')
    args=parser.parse_args()
    if args.build: build_library()
    elif args.pick: print(json.dumps(choose_track(previous=args.previous),ensure_ascii=True))
    else: print(json.dumps(catalog(),ensure_ascii=True))
