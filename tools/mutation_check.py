#!/usr/bin/env python3
"""Mutation check: break the program on purpose and confirm the test suite notices.
Runs the full suite once per mutant (~35 s each): python3 tools/mutation_check.py"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]
muts=[
 ('src/main.asm',' lda truce,x                 ; no attacks on the human while a truce holds\n lbne ai_next_dst',' lda truce,x\n lda #0\n lbne ai_next_dst','ai ignores truce'),
 ('src/main.asm',' jsr break_truce           ; attacking a truce partner voids the pact\n','','attack keeps truce'),
 ('src/engine_data.asm',' and #$6f                    ; bit 4','  and #$ff                    ; bit 4','disk blank keeps display'),
 ('src/engine_data.asm',' and #$7f\n ora #$10',' ora #$10','raster msb leak'),
 ('src/joystick.asm','CHORD_FRAMES','1','x'),
 ('src/diplomacy.asm',' bcc pt_refuse\n bne pt_accept',' bcs pt_refuse\n bne pt_accept','power compare inverted'),
 ('src/diplomacy.asm','pwr_add:\n clc\n adc pwr_lo\n sta pwr_lo\n bcc pa_done\n inc pwr_hi','pwr_add:\n clc\n adc pwr_lo\n sta pwr_lo\n bcc pa_done\n nop','8-bit power'),
 ('src/irq.asm',' sta $d019                   ; acknowledge raster IRQ\n',' nop\n','no irq ack'),
 ('src/main.asm',' jsr $FFB7                      ; READST\n and #$BF\n lbne disk_error\n cli\n jsr validate_snapshot',' jsr $FFB7\n cli\n jsr validate_snapshot','load ignores status'),
 ('src/main.asm',' jsr scratch_save_file\n',' \n','no scratch'),
 ('src/inventions.asm','ru_done:\n ldx simidx\n rts','ru_done:\n rts','x clobbered'),
 ('src/develop.asm',' lda ore,x\n cmp #6\n bcc dv_factory\n jmp build_lab',' lda ore,x\n cmp #6\n bcc dv_factory\n jmp build_factory','develop order'),
 ('src/main.asm',' lda #1\n sta $cc',' lda #0\n sta $cc','cursor blink on'),
 ('src/main.asm','elapsed_ok:\n clc\n adc frames\n sta frames\n cmp frames_per_tick\n bcc main_loop\n sec\n sbc frames_per_tick        ; keep remainder: drift-free tick clock\n sta frames','elapsed_ok:\n clc\n adc frames\n sta frames\n cmp frames_per_tick\n bcc main_loop\n lda #0\n sta frames','tick drift'),
]
survived=0
for f,old,new,name in muts:
    if name=='x': continue
    tmp=Path(tempfile.mkdtemp())
    shutil.copytree(SRC,tmp/'r',ignore=shutil.ignore_patterns('.git','__pycache__'))
    p=tmp/'r'/f;s=p.read_text()
    if old not in s: print('MUTATION NOT APPLICABLE',name);continue
    p.write_text(s.replace(old,new,1))
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=tmp/'r',capture_output=True,text=True)
    tail=r.stderr.strip().splitlines()[-1]
    print(('KILLED  ' if r.returncode else 'SURVIVED'),name,'|',tail)
    survived+=0 if r.returncode else 1
    shutil.rmtree(tmp)
sys.exit(1 if survived else 0)
