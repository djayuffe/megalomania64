; Resident callback: speech loading overwrites the intro-only RAM.
; Called after each disk byte, and while waiting. Frame subtraction handles wrap.
intro_poll:
 lda ic_active
 beq ic_poll_ok
 lda ic_skip
 bne ic_poll_abort
 lda vblank
 sec
 sbc ic_vb
 beq ic_poll_ok
 tax
 lda vblank
 sta ic_vb
ic_tick:
 txa
 pha
 clc
 lda ic_clock
 adc #70                    ; original VGA retraces, normalized on PAL and NTSC
 sta ic_clock
ic_logical_tick:
 lda ic_clock
 cmp ic_rate
 bcc ic_physical_done
 sec
 sbc ic_rate
 sta ic_clock
 lda ic_hold
 ora ic_hold+1
 beq ic_logical_tick
 lda ic_visible_mode
 cmp #3
 bne ic_tick_plain
 jsr credit_tick
ic_tick_plain:
 lda ic_hold
 bne ic_tick_low
 dec ic_hold+1
ic_tick_low:
 dec ic_hold
 jmp ic_logical_tick
ic_physical_done:
 pla
 tax
 dex
 bne ic_tick
ic_keys:
 lda ld_opened
 beq ic_keyboard
 jsr $ffcc                    ; GETIN otherwise reads the selected disk channel!
 jsr KGETIN
 pha
 ldx #2
 jsr $ffc6
 pla
 jmp ic_key_ready
ic_keyboard:
 jsr KGETIN
ic_key_ready:
 bne ic_poll_abort
 lda joy_raw
 and #16
 beq ic_poll_abort
ic_poll_ok:
 clc
 rts
ic_poll_abort:
 lda #1
 sta ic_skip
 sec
 rts



intro_poll_end:
