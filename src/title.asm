; --------------------------------------------------------------------------
; Intro picture: 160x200 multicolour bitmap (tools/make_intro.py) in VIC bank 1,
; bitmap $6000, screen RAM $5C00, colour data $5800 -> colour RAM. The raster-bar
; stack runs behind the logo (bars repaint $D020/$D021; only %00 pixels show it).
; Row 22 is %11-only, so PRESS FIRE colour-cycles through colour RAM.
; Leaves on any key or joystick FIRE and restores the VIC-bank-0 text map screen.
; --------------------------------------------------------------------------
INTRO_TEXT_ROW = 22

title_screen:
 lda #0
 sta $d015                   ; hide sprites on the title
 sta $c6                     ; drop any stale keystrokes from the KERNAL keyboard queue
 lda #$0b
 sta $d011                   ; display off while the VIC bank and colour RAM change
 ldx #0
ts_copy:
 lda intro_color,x
 sta COL,x
 lda intro_color+256,x
 sta COL+256,x
 lda intro_color+512,x
 sta COL+512,x
 lda intro_color+744,x
 sta COL+744,x
 inx
 bne ts_copy
 lda #0
 sta $d020
 sta $d021                   ; %00 pixels = black (raster bars repaint it)
 sta music_pos
 sta music_frame
 lda $dd00
 and #$fc
 ora #$02                    ; VIC bank 1: $4000-$7FFF
 sta $dd00
 lda #$78
 sta $d018                   ; screen RAM $5C00, bitmap $6000
 lda #$18
 sta $d016                   ; multicolour on, 40 columns
 lda #$3b
 sta $d011                   ; bitmap mode, display on
 lda #1
 sta title_bmp
 sta title_active            ; music variant 3 + raster bars on
title_wait:
 jsr wait_frame
 lda vblank
 lsr
 lsr
 sta titleph
 ldx #39
ts_color:
 txa
 clc
 adc titleph
 and #7
 tay
 lda title_pal,y
 sta COL+INTRO_TEXT_ROW*40,x
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
 sta title_bmp
 sta music_pos
 sta music_frame
 lda $dd00
 and #$fc
 ora #$03                    ; back to VIC bank 0
 sta $dd00
 lda #$1b
 sta $d011                   ; text mode, display on
 lda #$1e
 sta $d018                   ; screen $0400, charset $3800
 lda #6
 sta $d020
 sta $d021
 lda #3
 sta $d015
 rts

title_pal: !byte 2,10,7,1,7,3,14,6      ; hires-safe cycle for the PRESS FIRE row
