; --------------------------------------------------------------------------
; Title screen: static text + colour-cycled logo + raster bars (see irq.asm).
; Leaves on any key or joystick FIRE.
; --------------------------------------------------------------------------
TITLE_LINES = 7

title_screen:
 lda #0
 sta $d015                   ; hide sprites on the title
 sta $c6                     ; drop any stale keystrokes from the KERNAL keyboard queue
 jsr clear_screen
 ldx #0
ts_loop:
 stx titleidx
 lda title_tx,x
 sta text_x
 lda title_ty,x
 sta text_y
 lda title_ti,x
 sta ink
 lda title_tl,x
 sta PTR
 lda title_th,x
 sta PTR+1
 jsr print_text
 ldx titleidx
 inx
 cpx #TITLE_LINES
 bne ts_loop
 lda #0
 sta music_pos
 sta music_frame
 lda #1
 sta title_active            ; music variant 3 + raster bars on
title_wait:
 jsr wait_frame
 lda vblank
 lsr
 lsr
 sta titleph
 ldx #15
ts_color:
 txa
 clc
 adc titleph
 and #7
 tay
 lda title_pal,y
 sta COL+11*40+12,x
 dex
 bpl ts_color
 jsr KGETIN
 bne title_done
 lda joy_raw
 and #16
 bne title_wait
title_done:
 lda #0
 sta title_active
 sta music_pos
 sta music_frame
 lda #3
 sta $d015
 rts

title_tx: !byte 12,4,2,5,5,9,1
title_ty: !byte 11,13,15,17,19,21,23
title_ti: !byte 1,3,5,7,4,7,3         ; colours 0-7 only: 8-15 would switch the glyphs to multicolour
title_tl: !byte <ttl_0,<ttl_1,<ttl_2,<ttl_3,<ttl_4,<ttl_5,<ttl_6
title_th: !byte >ttl_0,>ttl_1,>ttl_2,>ttl_3,>ttl_4,>ttl_5,>ttl_6
title_pal: !byte 2,4,7,1,7,3,5,4
ttl_0: !text "MEGA-LO-MANIA 64",0
ttl_1: !text "ISLAND WARS  -  C64C EDITION 4.1",0
ttl_2: !text "28 ISLANDS - 10 EPOCHS - 4 FACTIONS",0
ttl_3: !text "BUILD  RESEARCH  ARM  CONQUER",0
ttl_4: !text "TRUCES  INVENTIONS  DISK SAVES",0
ttl_5: !text "PRESS FIRE OR ANY KEY",0
ttl_6: !text "UNOFFICIAL FAN-INSPIRED STRATEGY GAME",0
