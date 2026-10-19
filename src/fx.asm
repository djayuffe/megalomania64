; --------------------------------------------------------------------------
; Visual effects driven from the frame IRQ: border flashes, screen shake
; (horizontal scroll jitter) and pulsing sprite colours. Inactive on the title.
; --------------------------------------------------------------------------
; A = border colour, X = frames
fx_flash:
 sta fx_col
 stx fx_timer
 rts
; X = frames
fx_shake_start:
 stx shake_timer
 rts

fx_tick:
 lda title_active
 bne fx_done
 jsr orig_tick               ; marching army + conquest building icon
 lda fx_timer
 beq fx_shake
 dec fx_timer
 bne fx_blink
 lda border_col
 sta $d020                   ; resting frame colour
 jmp fx_shake
fx_blink:
 lda fx_timer
 and #2
 beq fx_rest
 lda fx_col
 bne fx_set
fx_rest:
 lda border_col
fx_set:
 sta $d020
fx_shake:
 lda shake_timer
 beq fx_sprites
 dec shake_timer
 lda shake_timer
 and #3
 tax
 lda shake_tab,x
 sta $d016
 lda shake_timer
 bne fx_sprites
 lda #$18
 sta $d016                   ; centred again
fx_sprites:
 lda vblank
 lsr
 lsr
 and #7
 tax
 lda cur_pal,x
 sta $d027                   ; cursor pulses yellow/white
 lda vblank
 lsr
 lsr
 lsr
 and #7
 tax
 lda src_pal,x
 sta $d028                   ; army-source marker pulses red
fx_done:
 rts

shake_tab: !byte $1b,$18,$1a,$19
cur_pal:   !byte 7,7,1,1,7,7,15,15
src_pal:   !byte 10,10,2,2,10,10,8,8
