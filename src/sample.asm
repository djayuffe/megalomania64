; --------------------------------------------------------------------------
; Sample player: the original Amiga 8SVX effects (stick, throw, musket, machine gun,
; cannon, missile, laser, explosion, grunt, orchestra hit, timpani), re-sampled to
; 5 kHz / 4 bit by tools/orig_convert.py and played through the SID master volume
; ($D418 low nibble). CIA 2 timer A raises an NMI at 5 kHz; nmi_entry -> sample_step.
; Samples are stored as packed nibbles (high nibble first).
; --------------------------------------------------------------------------
SMP_STICK   = 0
SMP_THROW   = 1
SMP_MUSKET  = 2
SMP_MG      = 3
SMP_CANNON  = 4
SMP_MISSILE = 5
SMP_LASER   = 6
SMP_XPLO    = 7
SMP_GRUNT   = 8
SMP_ORCH    = 9
SMP_TYMP    = 10
SMP_PAL     = 196               ; 985248 / 197  = 5001 Hz
SMP_NTSC    = 203               ; 1022727 / 204 = 5013 Hz

; Point the NMI vector at the sample player (once, at boot).
sample_init:
 lda #0
 sta nmi_busy
 lda #<nmi_entry
 sta $0318
 lda #>nmi_entry
 sta $0319
 sta $fffb                   ; RAM NMI vector for the brief KERNAL-out sample fetch
 lda #<nmi_entry
 sta $fffa
 jmp sample_stop

; A = sample id. Starts playback (replacing any sample in progress).
sample_play:
 pha
 jsr sample_stop              ; NMI off first: the state below is not touched by the NMI
 jsr sample_mute
 pla
 tax
 lda smp_off_lo,x
 sta smp_rd+1
 lda smp_off_hi,x
 sta smp_rd+2
 lda smp_len_lo,x
 sta smp_left
 lda smp_len_hi,x
 sta smp_left+1
 lda #0
 sta smp_half
sm_start:
 lda smp_speech
 beq sm_effect_rate
 lda $02a6
 beq sm_voice_ntsc
 lda #245
 bne sm_go
sm_voice_ntsc:
 lda #254
 bne sm_go
sm_effect_rate:
 lda $02a6                    ; KERNAL: PAL=1, NTSC=0
 beq sm_ntsc
 lda #SMP_PAL
 bne sm_go
sm_ntsc:
 lda #SMP_NTSC
sm_go:
 sta $dd04
 lda #0
 sta $dd05
 lda #$11
 sta $dd0e                    ; timer A: force-load, start, continuous
 lda #$81
 sta $dd0d                    ; timer A underflow -> NMI
 rts

sample_mute:
 lda #0
 sta $d406
 sta $d40d
 sta $d414                    ; sustain 0 / fastest release ...
 lda #$10
 sta $d404
 lda #$40
 sta $d40b
 lda #$20
 sta $d412                    ; ... and gates off: the SID voices are silent under the digi
 rts

; Stop any sample and restore the SID master volume. Preserves A, X, Y.
sample_stop:
 pha
 lda #$a5
 sta $d406                    ; envelopes back to the game values (main.asm)
 lda #$a6
 sta $d40d
 sta $d414
 lda #$7f
 sta $dd0d                    ; no CIA 2 NMI sources
 lda $dd0d                    ; acknowledge a pending one
 lda #0
 sta $dd0e
 sta smp_left
 sta smp_left+1
 sta smp_speech
 lda #$ff
 sta sp_queue
 lda #$0f
 sta $d418                    ; full volume, filters off
 pla
 rts

nmi_entry:
 pha
 txa
 pha
 lda $dd0d                    ; acknowledge; bit 7 = CIA 2 raised it (not the RESTORE key)
 bpl sm_neout
 lda nmi_busy
 bne sm_neout                ; VIC DMA can stretch a digi NMI past the next timer edge
 inc nmi_busy
 jsr sample_step
 dec nmi_busy
sm_neout:
 pla
 tax
 pla
 rti

; Output the next 4-bit sample to the SID volume register.
sample_step:
 lda smp_left
 ora smp_left+1
 lbeq sample_finished
 lda smp_speech
 beq smp_rd
 lda $01
 pha
 and #$fd
 sta $01
smp_rd:
 lda smp_data                 ; self-modified (absolute form forced: operand is a >$FF address): current sample byte
 ldx smp_speech
 beq sm_value
 tax
 pla
 sta $01
 txa
sm_value:
 ldx smp_half
 bne sm_low
 lsr
 lsr
 lsr
 lsr
 inx
 stx smp_half
 bne sm_out                   ; X = 1 here
sm_low:
 and #$0f
 ldx #0
 stx smp_half
 inc smp_rd+1
 bne sm_out
 inc smp_rd+2
 pha
 lda smp_speech
 beq sm_no_wrap
 lda smp_rd+2
 cmp #$80
 bne sm_no_wrap
 lda #$e0
 sta smp_rd+2
sm_no_wrap:
 pla
sm_out:
 sta $d418
 lda smp_left
 bne sm_dec
 dec smp_left+1
sm_dec:
 dec smp_left
 lda smp_left
 ora smp_left+1
 lbeq sample_finished
 rts

smp_left: !byte 0,0
smp_half: !byte 0
smp_prio: !byte 0
