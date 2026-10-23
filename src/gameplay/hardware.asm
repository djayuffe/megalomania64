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

* = $2700
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
 lda #<native_nmi
 sta $0318
 sta $fffa
 lda #>native_nmi
 sta $0319
 sta $fffb
 lda #<native_irq
 sta $fffe
 lda #>native_irq
 sta $ffff
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
 lda #$34
 sta $01
 jmp RUNTIME_MAIN
native_irq:
 pha
 txa
 pha
 tya
 pha
runtime_irq:
 lda $01
 pha
 lda #$36
 sta $01
 jsr runtime_tick
 jsr $ffea
 jsr $ff9f
 jmp native_return
runtime_tick:
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
 beq rt_running
rt_hold:
 inc io_frames
 bne rt_irq_exit
 inc io_frames+1
 jmp rt_irq_exit
rt_running:
 lda smp_left
 ora smp_left+1
 bne rt_hold
 lda mu_ready
 beq rt_irq_exit
 jsr original_music_tick
rt_irq_exit:
 rts
native_nmi:
 pha
 txa
 pha
 tya
 pha
 lda $01
 pha
 lda #$36
 sta $01
 lda $dd0d
 bpl native_return
 lda nmi_busy
 bne native_return
 inc nmi_busy
 jsr sample_step
 dec nmi_busy
native_return:
 pla
 sta $01
 pla
 tay
 pla
 tax
 pla
 rti
hw_frames:
 php
 sei
 sec
 lda native_frames
 sbc io_frames
 pha
 lda native_frames+1
 sbc io_frames+1
 tax
 pla
 plp
 rts
hw_key:
 lda $01
 pha
 lda #$36
 sta $01
 jsr native_key
 jmp hw_result
hw_open:
 sta PTR
 stx PTR+1
 lda $01
 pha
 lda #$36
 sta $01
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
 jmp hw_result
rt_open_bad:
 jsr rt_close
 lda #0
 jmp hw_result
hw_read:
 lda $01
 pha
 lda #$36
 sta $01
 jsr ld_read
 bcc rt_read_ok
 lda #1
 sta hw_error
 lda #0
rt_read_ok:
 jmp hw_result
hw_close:
 lda $01
 pha
 lda #$36
 sta $01
 jsr rt_close
 lda #0
hw_result:
 sta hw_value
 pla
 sta $01
 lda hw_value
 ldx #0
 rts
rt_close:
 jsr ld_close
 lda #0
 sta music_hold
 lda $d011
 and #$7f
 ora #$10
 sta $d011
 rts
hw_play:
 sta hw_play_lo
 stx hw_play_hi
 lda $01
 pha
 lda #$36
 sta $01
 jsr sample_stop
 jsr sample_mute
 lda hw_play_hi
 sta smp_left+1
 lda hw_play_lo
 sta smp_left
 lda #0
 sta smp_half
 sta smp_rd+1
 lda #$ef
 sta smp_rd+2
 lda clip_voice
 sta smp_speech
 jsr sm_start
 lda #0
 jmp hw_result
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
hw_file:
 lda hw_slot
 clc
 adc #48
 sta hw_save_name+5
 sta hw_scratch+8
 lda #6
 ldx #<hw_save_name
 ldy #>hw_save_name
 jsr $ffbd
 lda #1
 ldx devnum
 ldy #0
 jsr $ffba
 rts
hw_io_begin:
 lda #1
 sta music_hold
 jsr sample_stop
 lda #0
 sta $d015
 lda $d011
 and #$6f
 sta $d011
 rts
hw_store:
 sta hw_slot
 lda $01
 pha
 lda #$36
 sta $01
 jsr hw_io_begin
 jsr hw_file
 lda #9
 ldx #<hw_scratch
 ldy #>hw_scratch
 jsr $ffbd
 lda #15
 ldx devnum
 ldy #15
 jsr $ffba
 jsr $ffc0
 lda #15
 jsr $ffc3
 jsr hw_file
 lda #$80
 sta PTR
 lda #$3f
 sta PTR+1
 lda #PTR
 ldx #0
 ldy #$69
 jsr $ffd8
 bcs hw_io_bad
 jsr hw_file
 lda #1
 bne hw_load_go
hw_restore:
 sta hw_slot
 lda $01
 pha
 lda #$36
 sta $01
 jsr hw_io_begin
 jsr hw_file
 lda #0
hw_load_go:
 ldx #$80
 ldy #$3f
 jsr $ffd5
 bcs hw_io_bad
 cpx #0
 bne hw_io_bad
 cpy #$69
 bne hw_io_bad
 jsr $ffb7
 and #$bf
 bne hw_io_bad
 lda #1
 bne hw_io_done
hw_io_bad:
 lda #0
hw_io_done:
 pha
 jsr rt_close
 pla
 jmp hw_result
; Back up/restore the complete snapshot in RAM under I/O/KERNAL. All callers
; and IRQ/NMI entries remain outside this temporary staging area.
hw_shadow:
 pha
 lda #$36
 sta $01
 jsr sample_stop
 lda #$34
 sta $01
 lda #$80
 sta PTR
 lda #$3f
 sta PTR+1
 lda #0
 sta CPTR
 lda #$d4
 sta CPTR+1
 pla
 beq hw_shadow_ready
 ldx PTR
 lda CPTR
 sta PTR
 stx CPTR
 ldx PTR+1
 lda CPTR+1
 sta PTR+1
 stx CPTR+1
hw_shadow_ready:
 jsr hw_count_init
 ldy #0
hw_shadow_byte:
 lda (PTR),y
 sta (CPTR),y
 iny
 bne hw_shadow_next
 inc PTR+1
 inc CPTR+1
hw_shadow_next:
 jsr hw_count_down
 bne hw_shadow_byte
 rts
hw_count_init:
 lda #$80
 sta hw_count
 lda #$29
 sta hw_count+1
 rts
hw_count_down:
 lda hw_count
 bne hw_count_low
 dec hw_count+1
hw_count_low:
 dec hw_count
 lda hw_count
 ora hw_count+1
 rts
hw_crc:
 lda #$ff
 sta crc_value
 sta crc_value+1
 lda #$80
 sta PTR
 lda #$3f
 sta PTR+1
 jsr hw_count_init
 ldy #0
hw_crc_byte:
 lda (PTR),y
 eor crc_value+1
 sta crc_value+1
 ldx #8
hw_crc_bit:
 asl crc_value
 rol crc_value+1
 bcc hw_crc_next
 lda crc_value
 eor #$21
 sta crc_value
 lda crc_value+1
 eor #$10
 sta crc_value+1
hw_crc_next:
 dex
 bne hw_crc_bit
 iny
 bne hw_crc_count
 inc PTR+1
hw_crc_count:
 jsr hw_count_down
 bne hw_crc_byte
 lda crc_value
 ldx crc_value+1
 rts
; Stable busy check across the NMI's 16-bit decrement/borrow.
hw_audio_busy:
 lda smp_left
 ora smp_left+1
 ora smp_left
 ldx #0
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
hw_value: !byte 0
hw_slot: !byte 0
io_frames: !word 0
hw_count: !word 0
crc_value: !word 0
hw_play_lo: !byte 0
hw_play_hi: !byte 0
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
* = $33a0
hw_save_name: !text "NSAVE0"
hw_scratch: !text "S0:NSAVE0"
* = $3340
!source "../music_data.asm"
* = $3700
!bin "../../assets/cursor_sprite.bin"
* = $3740
!bin "../../assets/source_sprite.bin"
* = $3800
!bin "../../assets/charset.bin"
