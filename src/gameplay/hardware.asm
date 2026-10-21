; Native runtime support. Existing, verified SID and NMI drivers are reused.
PTR = $fb
CPTR = $fd
smp_data = $ef00
smp_end = $0000
* = $0900
!source "../music.asm"
* = $0c40
!source "../sample.asm"
* = $0e80
!source "../loader.asm"
support_loader_end:

* = $2800
runtime_start:
 sei
 lda #$36
 sta $01
 lda #$7f
 sta $dc0d
 sta $dd0d
 lda $dc0d
 lda $dd0d
 lda #0
 sta PTR
 lda #$70
 sta PTR+1
 ldx #16
 ldy #0
 lda #0
rt_clear:
 sta (PTR),y
 iny
 bne rt_clear
 inc PTR+1
 dex
 bne rt_clear
 lda #$ff
 sta ZP_STACK
 lda #$c3
 sta ZP_STACK+1
 lda #$1b
 sta $d011
 lda #8
 sta $d016
 lda #$1e
 sta $d018
 lda $dd00
 and #$fc
 ora #3
 sta $dd00
 lda #6
 sta $d020
 sta $d021
 lda #0
 sta $d025
 lda #15
 sta $d026
 lda #1
 sta $cc
 lda #0
 sta $9d
 jsr sample_init
 lda #<runtime_irq
 sta $0314
 lda #>runtime_irq
 sta $0315
 lda #250
 sta $d012
 lda #1
 sta $d01a
 lda #$ff
 sta $d019
 cli
 lda #1
 jsr music_load
 jmp RUNTIME_MAIN
runtime_irq:
 lda $d019
 and #1
 beq rt_irq_exit
 lda #$ff
 sta $d019
 inc native_frames
 bne rt_music
 inc native_frames+1
rt_music:
 jsr native_animate
 lda music_hold
 bne rt_irq_exit
 lda smp_left
 ora smp_left+1
 bne rt_irq_exit
 lda mu_ready
 beq rt_irq_exit
 jsr original_music_tick
rt_irq_exit:
 jmp $ea31
hw_frames:
 php
 sei
 lda native_frames
 ldx native_frames+1
 plp
 rts
hw_key:
 jmp native_key
hw_open:
 sta PTR
 stx PTR+1
 ldy #0
rt_name:
 lda (PTR),y
 beq rt_name_done
 iny
 cpy #16
 bcc rt_name
rt_name_done:
 tya
 ldx PTR
 ldy PTR+1
 pha
 lda #1
 sta music_hold
 lda #0
 sta hw_error
 sta $d015
 lda $d011
 and #$6f
 sta $d011
 pla
 jsr ld_open
 bcs rt_open_bad
 lda #1
 ldx #0
 rts
rt_open_bad:
 jsr hw_close
 lda #0
 tax
 rts
hw_read:
 jsr ld_read
 bcc rt_read_ok
 lda #1
 sta hw_error
 lda #0
rt_read_ok:
 ldx #0
 rts
hw_close:
 jsr ld_close
 lda #0
 sta music_hold
 lda $d011
 and #$7f
 ora #$10
 sta $d011
 rts
hw_play:
 pha
 txa
 pha
 jsr sample_stop
 jsr sample_mute
 pla
 sta smp_left+1
 pla
 sta smp_left
 lda #0
 sta smp_half
 sta smp_rd+1
 lda #$ef
 sta smp_rd+2
 lda clip_voice
 sta smp_speech
 jmp sm_start
sample_finished:
 jmp sample_stop
intro_poll:
 clc
 rts
get_device:
 lda $ba
 cmp #8
 bcs rt_have_device
 lda #8
rt_have_device:
 sta devnum
 rts
support_end:

* = $3280
; Port 2 directions and fire are edge-triggered, alongside the keyboard.
native_key:
 jsr $ffe4
 bne native_key_done
 lda $dc00
 and #$1f
 cmp native_joy
 beq native_key_none
 sta native_joy
 lsr
 bcc native_key_up
 lsr
 bcc native_key_down
 lsr
 bcc native_key_left
 lsr
 bcc native_key_right
 lsr
 bcc native_key_fire
native_key_none:
 lda #0
 beq native_key_done
native_key_up:
 lda #87
 bne native_key_done
native_key_down:
 lda #83
 bne native_key_done
native_key_left:
 lda #65
 bne native_key_done
native_key_right:
 lda #68
 bne native_key_done
native_key_fire:
 lda #13
native_key_done:
 ldx #0
 rts
native_animate:
 lda native_frames
 lsr
 lsr
 lsr
 and #3
 clc
 adc #$c5
 sta $07f9
 rts
native_key_end:
* = $3322
native_joy: !byte $1f
* = $3300
native_frames: !word 0
hw_error: !byte 0
clip_voice: !byte 0
music_hold: !byte 0
soundtime: !byte 0
sfx_cur_prio: !byte 0
devnum: !byte 8
sp_queue: !byte $ff
smp_speech: !byte 0
sid_8580: !byte 0
nmi_busy: !byte 0
fx_ready: !byte 0
ld_opened: !byte 0
ld_left: !word 0
ld_eof: !byte 0
ld_error: !byte 0
ld_status: !byte 0
ld_value: !byte 0
ld_write: !byte 0
ld_rx: !byte 0
ld_ry: !byte 0
ld_count: !byte 0
ld_repeat: !byte 0
smp_off_lo: !byte 0
smp_off_hi: !byte $ef
smp_len_lo: !byte 0
smp_len_hi: !byte 0
fx_off_lo: !byte 0
fx_off_hi: !byte $ef
fx_len_lo: !byte 0
fx_len_hi: !byte 0
* = $3340
!source "../music_data.asm"
* = $3700
!bin "../../assets/cursor_sprite.bin"
* = $3740
!bin "../../assets/source_sprite.bin"
* = $3800
!bin "../../assets/charset.bin"
