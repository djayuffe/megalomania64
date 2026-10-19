; Volatile engine state (not saved). Zero/idle values are loaded with the PRG.
vblank:       !byte 0         ; frame counter bumped by the raster IRQ
lastvb:       !byte 0
elapsed:      !byte 0
joy_raw:      !byte 31        ; port 2 sampled in the IRQ, active low
joycur:       !byte 31
joyedge:      !byte 0
joyfire:      !byte 0         ; 0 idle, 1 FIRE tap candidate, 2 chord in progress
joychord:     !byte 15
joycount:     !byte 0
irq_stage:    !byte 0         ; 0 = frame IRQ, 1.. = title raster bars
irq_line:     !byte 0
title_active: !byte 0
music_over:   !byte 0         ; tune index (4 victory, 5 defeat) overriding the epoch tune, 0 = none
sfx_f:        !byte 0
sfx_sw:       !byte 0
sfx_w:        !byte 0
sfx_cur_prio: !byte 0
cu_len:       !byte 0
cu_col:       !byte 0
cu_x:         !byte 0
border_col:   !byte 6
fx_timer:     !byte 0
fx_col:       !byte 0
shake_timer:  !byte 0
music_hold:   !byte 0         ; 1 = music/SFX sequencer paused (intro)
it:           !byte 0         ; intro: reveal frame counter (saturates at 52)
ip_clock:     !byte 0         ; intro: parade clock (saturates at 255)
ip_arrived:   !byte 0         ; intro: soldiers that reached their slot
ip_msb:       !byte 0
ip_k:         !byte 0
rv_k:         !byte 0
rv_hi:        !byte 0
ip_st:        !fill 8,0       ; 0 waiting, 1 walking, 2 arrived
ip_xlo:       !fill 8,0
ip_xhi:       !fill 8,0
ts_save:      !fill 31,0      ; VIC sprite registers saved around the intro
title_bmp:    !byte 0         ; 1 while the multicolour intro bitmap is shown
titleidx:     !byte 0
titleph:      !byte 0
devnum:       !byte 8         ; device used for SAVE/LOAD (see get_device)
pwr_lo:       !byte 0
pwr_hi:       !byte 0
pp_lo:        !byte 0
pp_hi:        !byte 0
powf:         !byte 0
pt_faction:   !byte 0
dt_idx:       !byte 0
pe_idx:       !byte 0
msgbuf:       !fill 42,0
saved_d015:   !byte 3

; The KERNAL serial-bus routines are cycle-sensitive: VIC badline and sprite DMA
; can break them. Blank the screen and switch sprites off around every disk access.
disk_begin:
 jsr sample_stop             ; no NMI while the serial bus is busy
 lda $d015
 sta saved_d015
 lda #0
 sta $d015
 lda $d011
 and #$6f                    ; bit 4 = display off; bit 7 (raster compare MSB) stays 0
 sta $d011
 rts
disk_end:
 lda $d011
 and #$7f
 ora #$10                    ; display back on
 sta $d011
 lda saved_d015
 sta $d015
 rts

; Device for disk I/O: whatever the KERNAL last used (the drive we were
; loaded from) when it is a disk unit, else 8.
get_device:
 lda $ba
 cmp #8
 bcc gd_default
 cmp #12
 bcc gd_store
gd_default:
 lda #8
gd_store:
 sta devnum
 rts
