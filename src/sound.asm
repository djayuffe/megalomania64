; --------------------------------------------------------------------------
; Sound: table-driven SFX on SID voice 1 (priority, per-frame pitch sweep, gate
; retrigger) + a two-voice tracker on voices 2/3 (pulse lead with PWM, sawtooth
; bass, gate retrigger per note). Run from the frame IRQ (irq.asm).
; Tunes: 0 ancient, 1 medieval, 2 industrial, 3 title, 4 victory, 5 defeat.
; --------------------------------------------------------------------------
SFX_OK = 0
SFX_NO = 1
SFX_ATTACK = 2
SFX_CAPTURE = 3
SFX_LOST = 4
SFX_INVENT = 5
SFX_TRUCE = 6
SFX_BUILD = 7
SFX_DISK = 8
SFX_TICK = 9
SFX_WIN = 10
SFX_LOSE = 11
SFX_REPULSE = 12

; A = effect id. A running effect is only replaced by one of equal/higher priority.
sfx_play:
 tax
 jsr speech_event
 bcs sp_skip
 jsr sfx_sample              ; original Amiga sample instead of the SID effect?
 bcs sp_skip
 lda soundtime
 beq sp_go
 lda sfx_prio,x
 cmp sfx_cur_prio
 bcc sp_skip
sp_go:
 lda sfx_prio,x
 sta sfx_cur_prio
 lda sfx_fhi,x
 sta sfx_f
 sta $d401
 lda sfx_flo,x
 sta $d400
 lda sfx_sweep,x
 sta sfx_sw
 lda sfx_pw,x
 sta $d403
 lda #0
 sta $d402
 lda sfx_ad,x
 sta $d405
 lda sfx_sr,x
 sta $d406
 lda sfx_wave,x
 sta sfx_w
 and #$fe
 sta $d404                   ; gate off, then on: retrigger the envelope
 lda sfx_w
 sta $d404
 lda sfx_len,x
 sta soundtime
sp_skip:
 rts

; X = effect id. Returns carry set when the SID effect must be skipped: either the
; original sample for this event just started, or a sample is still playing (the SID
; voices are muted for the duration). Preserves X.
sfx_sample:
 lda fx_valid
 beq ss_invalid
 txa
 pha
 lda sfx_smp,x
 cmp #$ff
 beq ss_none
 cmp #$fe
 bne ss_have
 ldy epoch                   ; attack: the weapon of the current epoch
 lda attack_smp,y
ss_have:
 tay
 lda smp_left
 ora smp_left+1
 beq ss_go
 lda sfx_prio,x
 cmp smp_prio
 bcc ss_busy                 ; a more important sample is still playing
ss_go:
 lda sfx_prio,x
 sta smp_prio
 tya
 jsr sample_play
ss_busy:
 pla
 tax
 sec
 rts
ss_none:
 pla
 tax
 lda smp_left
 ora smp_left+1
 cmp #1                      ; carry set when a sample is playing (non-zero)
 rts

ss_invalid:
 clc
 rts

; sample per SFX id ($ff none, $fe by epoch)
sfx_smp:   !byte $ff,$ff,$fe,SMP_XPLO,SMP_GRUNT,$ff,$ff,$ff,$ff,$ff,SMP_ORCH,SMP_TYMP,SMP_MUSKET
attack_smp: !byte SMP_STICK,SMP_STICK,SMP_THROW,SMP_THROW,SMP_MUSKET,SMP_MUSKET,SMP_MG,SMP_CANNON,SMP_MISSILE,SMP_LASER

beep_ok:
 lda #SFX_OK
 jmp sfx_play
beep_no:
 lda #SFX_NO
 jmp sfx_play

;            ok  no  atk cap lost inv trc bld dsk tck win lose rep
sfx_fhi:   !byte 24, 7, 44, 22, 30, 20, 28, 56, 18, 40, 20, 24, 20
sfx_flo:   !byte $30,$80,0,0,0,0,0,0,0,0,0,0,0
sfx_sweep: !byte 3, 0,$fe, 3,$fe, 2, 1,$fa, 2, 0, 1,$ff,$ff
sfx_wave:  !byte $11,$21,$81,$41,$21,$11,$41,$81,$11,$11,$41,$21,$81
sfx_ad:    !byte $08,$08,$00,$08,$08,$18,$08,$00,$18,$00,$28,$28,$08
sfx_sr:    !byte $a6,$a6,$a8,$a8,$a8,$a8,$a8,$a4,$a8,$a2,$c9,$c9,$a8
sfx_pw:    !byte 8, 8, 8, 8, 8, 8, 6, 8, 8, 8, 8, 8, 8
sfx_len:   !byte 6, 9,12,16,14,22,10, 4,12, 2,60,70,10
sfx_prio:  !byte 1, 2, 3, 4, 4, 4, 3, 1, 3, 0, 6, 6, 3

sound_tick:
 lda smp_left
 ora smp_left+1
 ora music_hold
 bne st_quiet                ; sample playing (SID voices muted) or intro hold: music/SFX wait
 lda soundtime
 beq st_music
 dec soundtime
 bne st_sweep
 lda sfx_w
 and #$fe
 sta $d404                   ; gate off: release
 lda #0
 sta sfx_cur_prio
 beq st_music
st_sweep:
 lda sfx_f
 clc
 adc sfx_sw
 sta sfx_f
 sta $d401
st_music:
 jmp music_tick
st_quiet:
 rts

; Voice 2 = pulse lead (PWM), voice 3 = sawtooth bass. Each step releases both notes
; and re-gates them two frames later so repeated notes are articulated.
music_tick:
 lda mu_ready
 beq music_port_score
 lda music_over
 bne music_port_score
 jmp original_music_tick
music_port_score:
 ldy music_over
 bne music_have
 ldy title_active
 beq music_game
 ldy #3
 bne music_have
music_game:
 ldy epoch
 lda music_variant,y
 tay
music_have:
 inc music_frame
 lda music_frame
 cmp music_tempo,y
 bcc mt_hold
 lda #0
 sta music_frame
 tya
 asl
 asl
 asl
 asl
 ora music_pos
 tax
 lda melody_lo,x
 sta $d407
 lda melody_hi,x
 sta $d408
 lda bass_lo,x
 sta $d40e
 lda bass_hi,x
 sta $d40f
 lda #$40
 sta $d40b                   ; pulse, gate off
 lda #$20
 sta $d412                   ; sawtooth, gate off
 inc music_pos
 lda music_pos
 and #15
 sta music_pos
 rts
mt_hold:
 lda music_frame
 cmp #2
 bne mt_pwm
 lda #$41
 sta $d40b                   ; gate on: attack again
 lda #$21
 sta $d412
mt_pwm:
 lda vblank
 lsr
 and #7
 ora #4
 sta $d40a                   ; pulse width wobble
 rts
