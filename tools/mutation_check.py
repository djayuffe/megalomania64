#!/usr/bin/env python3
"""Mutation check: break the program on purpose and confirm the test suite notices.
Runs the full suite once per mutant (~35 s each): python3 tools/mutation_check.py [file-substring, e.g. orig]"""
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

 ('src/sound.asm',' lda sfx_prio,x\n cmp sfx_cur_prio\n bcc sp_skip',' lda sfx_prio,x\n cmp sfx_cur_prio\n bcs sp_skip','sfx priority inverted'),
 ('src/sound.asm',' lda #$41\n sta $d40b                   ; gate on: attack again',' lda #$40\n sta $d40b','music never re-gated'),
 ('src/fx.asm',' lda #$18\n sta $d016                   ; centred again',' nop','shake never recentres'),
 ('src/hud.asm','hud_rowcol: !byte 0, 0, 0, 3, 0, 1, 7,','hud_rowcol: !byte 0, 0, 0, 3, 0, 1, 14,','hud multicolour text'),
 ('src/hud.asm',' pha\n tya\n pha\n ldy epoch',' ldy epoch','set_border clobbers Y'),
 ('src/title.asm',' lda #$78\n sta $d018                   ; screen RAM $5C00, bitmap $6000',' lda #$38\n sta $d018','intro wrong bitmap base'),

 ('src/orig.asm',' lda #0\n sbc #0\n sta mdx_i\n jsr march_x8',' lda #0\n sta mdx_i\n jsr march_x8','march loses sign of leftward step'),
 ('src/orig.asm',' lsr\n lsr\n and #3\n clc\n adc #$c8',' lsr\n lsr\n and #0\n clc\n adc #$c8','walk cycle frozen'),
 ('src/orig.asm','ole_b:\n tax\n lda build_off_hi,x','ole_b:\n tax\n inx\n lda build_off_hi,x','building icon off by one epoch'),
 ('src/orig.asm',' lda $d015\n and #$fb\n sta $d015                   ; arrived',' nop','army sprite never hides'),
]
survived=0
only=sys.argv[1] if len(sys.argv)>1 else ''
for f,old,new,name in muts:
    if name=='x' or only not in f: continue
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
