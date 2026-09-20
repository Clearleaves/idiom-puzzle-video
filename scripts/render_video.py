"""Render a four-clue idiom video from an original still and an episode JSON."""
import argparse, json, math, os, re, shutil, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',type=Path,required=True)
parser.add_argument('--config',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--work-dir',type=Path,required=True)
parser.add_argument('--font',type=Path)
parser.add_argument('--font-bold',type=Path)
parser.add_argument('--ffmpeg')
parser.add_argument('--overwrite',action='store_true')
args=parser.parse_args()
cfg=json.loads(args.config.read_text(encoding='utf-8-sig'))
def fail(message): parser.error(message)
if not isinstance(cfg,dict):fail('Config must be a JSON object')
idiom=cfg.get('idiom','')
if not isinstance(idiom,str) or len(idiom)!=4 or not all('\u4e00'<=c<='\u9fff' for c in idiom):fail('idiom must contain exactly four Chinese characters')
clues=cfg.get('clues')
if not isinstance(clues,list) or len(clues)!=4 or not all(isinstance(x,str) and x.strip() for x in clues):fail('clues must contain four nonempty strings')
if not isinstance(cfg.get('explanation'),str) or not cfg['explanation'].strip():fail('explanation is required')
defaults={'title':'看图猜成语','subtitle':'四个线索，你能连起来吗？','hint':'提示：试试谐音','closing':'你答对了吗？明天再猜一道'}
for key,value in defaults.items():
    cfg.setdefault(key,value)
    if not isinstance(cfg[key],str) or not cfg[key].strip():fail(key+' must be a nonempty string')
def integer(key,default,low,high):
    value=cfg.get(key,default)
    if type(value) is not int or not low<=value<=high:fail(f'{key} must be an integer between {low} and {high}')
    return value
episode=integer('episode',1,1,999)
GUESS=integer('guess_seconds',11,5,25)
ANSWER=integer('answer_seconds',5,3,10)
W,H,FPS,DURATION=1080,1920,24,GUESS+ANSWER
stem=cfg.get('filename',idiom)
if not isinstance(stem,str) or not re.fullmatch(r'[\w\-\u4e00-\u9fff]{1,80}',stem) or stem.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:fail('filename must be a safe filename stem without extensions or separators')
OUT=args.output_dir.resolve(); WORK=args.work_dir.resolve()
if OUT==WORK:fail('Use separate output and working directories')
out=OUT/(stem+'.mp4'); cover=OUT/(stem+'_封面.jpg'); report=OUT/(stem+'_检查.json')
if not args.overwrite and any(p.exists() for p in (out,cover,report)):fail('Output already exists; change filename or explicitly use --overwrite')
regular=args.font or Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/msyh.ttc'
bold=args.font_bold or (regular if args.font else Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/msyhbd.ttc')
if not regular.is_file() or not bold.is_file():fail('Chinese font not found; provide --font and optionally --font-bold')
ff=args.ffmpeg or shutil.which('ffmpeg')
if not ff:
    try:
        import imageio_ffmpeg
        ff=imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        fail('FFmpeg not found. Install FFmpeg or imageio-ffmpeg, or pass --ffmpeg')
with Image.open(args.image) as source:
    if abs(source.width/source.height-9/16)>.035:fail('Input must be approximately 9:16; regenerate or prepare the correct composition')
    base=source.convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
fonts={}
def font(n,bold=False):
    k=(n,bold)
    if k not in fonts: fonts[k]=ImageFont.truetype(str(globals()['bold'] if bold else regular),n)
    return fonts[k]
ink='#492f20'; accent='#a44724'
def centered(d,text,y,size,color=ink,bold=False):
    while size>18 and d.textlength(text,font=font(size,bold))>W-160: size-=1
    d.text((W//2,y),text,font=font(size,bold),fill=color,anchor='mt')

def text_in_box(d,text,box,size,color=ink,bold=False):
    """Center the visible glyph bounds, not the font ascent or top anchor."""
    face=font(size,bold)
    left,top,right,bottom=d.textbbox((0,0),text,font=face)
    x0,y0,x1,y1=box
    x=(x0+x1-(right-left))/2-left
    y=(y0+y1-(bottom-top))/2-top
    d.text((x,y),text,font=face,fill=color)
def frame(t):
    # A gentle camera move preserves the complete puzzle throughout.
    scale=1+0.012*math.sin(math.pi*min(t,GUESS)/GUESS)
    sw,sh=round(W*scale),round(H*scale)
    im=base.resize((sw,sh),Image.Resampling.BICUBIC).crop(((sw-W)//2,(sh-H)//2,(sw+W)//2,(sh+H)//2))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((350,124,730,183),radius=29,fill='#ead4ad')
    centered(d,f'每日一猜  /  第 {episode:03d} 期',135,29)
    centered(d,cfg['title'],222,100,bold=True)
    centered(d,cfg['subtitle'],355,39)
    if t<GUESS:
        remaining=max(1,math.ceil(GUESS-t))
        d.ellipse((466,459,614,607),fill='#fff6e5',outline='#d3b67e',width=3)
        d.arc((466,459,614,607),-90,-90+360*(GUESS-t)/GUESS,fill=accent,width=9)
        text_in_box(d,str(remaining),(466,459,614,607),74,accent,True)
        # Sequential underlines point to the four objects without hiding them.
        if 1.0<t<min(5.0,GUESS):
            idx=min(3,int(t-1.0)); cx=[160,400,655,930][idx]
            d.rounded_rectangle((cx-65,1283,cx+65,1292),radius=4,fill=accent)
        for i in range(4):
            x=279+i*140
            d.rounded_rectangle((x,1360,x+112,1472),radius=22,fill='#fff7e9',outline='#d8bd91',width=2)
            text_in_box(d,'?',(x,1360,x+112,1472),62,'#b48a50',True)
        centered(d,cfg['hint'] if t>=GUESS*.55 else '先别急，按从左到右猜一猜',1535,40,accent)
    else:
        centered(d,'答案揭晓',475,44,accent,True)
        # Reveal card is below the objects so all clues remain visible.
        d.rounded_rectangle((105,1310,975,1635),radius=38,fill='#fff6e6',outline='#d5b67d',width=3)
        centered(d,' '.join(idiom),1355,99,accent,True)
        centered(d,' + '.join(clues),1490,43)
        centered(d,cfg['explanation'],1560,34)
    centered(d,cfg['closing'] if t>=GUESS else '趣味谐音谜题 · 仅供娱乐',1710,33)
    centered(d,'AI 生成画面',1780,25,'#806b53')
    d.rectangle((0,H-8,int(W*t/DURATION),H),fill=accent)
    return im

# Original synthesized soundtrack: soft plucked pentatonic notes and clear ticks.
sr=44100
audio=np.zeros(sr*DURATION,dtype=np.float64)
def note(start,freq,dur,volume):
    a=int(start*sr); n=min(int(dur*sr),len(audio)-a)
    if n<=0:return
    tt=np.arange(n)/sr
    envelope=(1-np.exp(-tt*65))*np.exp(-tt*3.5)*np.minimum(1,(dur-tt)*12)
    sig=(np.sin(2*np.pi*freq*tt)+.23*np.sin(4*np.pi*freq*tt))*envelope*volume
    audio[a:a+n]+=sig
melody=[523.25,659.25,783.99,659.25,587.33,659.25,880,783.99]
for i in range(max(1,(DURATION-2)*2)):note(i*.5,melody[i%8],.75,.065)
for i in range(1,GUESS):note(i,1046.5,.12,.10 if i<GUESS-3 else .17)
for k,f in enumerate([523.25,659.25,783.99,1046.5]):note(GUESS+k*.12,f,1.6,.16)
audio*=np.minimum(1,np.arange(len(audio))/sr/.25)*np.minimum(1,(len(audio)-np.arange(len(audio)))/sr/1.2)
with wave.open(str(WORK/'music.wav'),'wb') as wf:
    wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(sr);wf.writeframes((np.clip(audio,-.95,.95)*32767).astype('<i2').tobytes())

temporary=WORK/(stem+'.partial.mp4')
cmd=[ff,'-y','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-','-i',str(WORK/'music.wav'),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(temporary)]
with open(WORK/'render.log','w',encoding='utf-8') as log:
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
    try:
        for i in range(FPS*DURATION):
            im=frame(i/FPS)
            if i in (0,int(GUESS*.7)*FPS,(GUESS+1)*FPS):im.save(WORK/f'check_{i//FPS}.jpg')
            process.stdin.write(im.tobytes())
        process.stdin.close()
        rc=process.wait(timeout=120)
        if rc:raise RuntimeError('FFmpeg failed; inspect '+str(WORK/'render.log'))
    except BaseException:
        process.kill();process.wait()
        raise
check=subprocess.run([ff,'-v','error','-i',str(temporary),'-map','0:v:0','-map','0:a:0','-f','null','-'],capture_output=True,timeout=120)
if check.returncode:raise RuntimeError('Video decode check failed: '+check.stderr.decode('utf-8',errors='replace'))
if not args.overwrite and any(p.exists() for p in (out,cover,report)):raise FileExistsError('Output appeared during rendering; choose a new filename')
shutil.copyfile(temporary,out)
frame(0).save(cover,quality=95)
metadata={'idiom':idiom,'episode':episode,'width':W,'height':H,'fps':FPS,'duration_seconds':DURATION,'frame_count':FPS*DURATION,'audio_peak':float(np.max(np.abs(audio))),'full_decode_passed':True,'audio_stream_present':True,'manual_visual_review':'required','file_bytes':out.stat().st_size}
report.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'video':str(out),'cover':str(cover),'report':str(report)},ensure_ascii=True))
