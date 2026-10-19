; --------------------------------------------------------------------------
; Intro (v4.4). Built from the decoded original assets; the original Amiga intro itself
; could not be recovered, so this is a new sequence:
;   1. Reveal: the 160x200 multicolour picture (tools/make_intro.py) in VIC bank 1
;      (bitmap $6000, screen RAM $5C00, colour data $5800) opens from the middle row
;      outwards, 4 frames per step, with the original orchestra-hit sample.
;   2. Parade: eight soldiers, one per epoch, drawn from the original Amiga sprites
;      ($4000, pointers 0..31), walk in from the left to their slots; each arrival plays
;      the epoch's original weapon sample.
;   3. Title: raster bars behind the logo, title tune, PRESS FIRE colour cycle.
; Any key or joystick FIRE leaves at once and restores the VIC-bank-0 text screen and the
; game's sprite registers. Screen RAM is revealed from intro_screen_src ($4D00); colour RAM
; and screen RAM start black so %01/%10/%11 pixels stay invisible until their row opens.
; Row 22 is %11-only, so PRESS FIRE colour-cycles through colour RAM.
; --------------------------------------------------------------------------
INTRO_TEXT_ROW = 22
REVEAL_FRAMES = 52           ; 13 steps x 4 frames
IP_Y = 200                   ; sprite Y of the parade (just above the text band)
IP_SPEED = 3

title_screen:
 lda #0
 sta $d015                   ; hide sprites on the title
 sta $c6                     ; drop any stale keystrokes from the KERNAL keyboard queue
 sta it
 sta ip_clock
 sta ip_arrived
 lda #$0b
 sta $d011                   ; display off while the VIC bank and colour RAM change
 ldx #7
ts_save_sp:                  ; keep the game's sprite registers
 lda $d000,x
 sta ts_save,x
 lda $d008,x
 sta ts_save+8,x
 dex
 bpl ts_save_sp
 lda $d010
 sta ts_save+16
 ldx #9
ts_save_col:
 lda $d025,x
 sta ts_save+17,x
 dex
 bpl ts_save_col
 lda $d017
 sta ts_save+27
 lda $d01b
 sta ts_save+28
 lda $d01c
 sta ts_save+29
 lda $d01d
 sta ts_save+30
 ldx #0
 txa
ts_clear:                    ; colour RAM + screen RAM black: nothing shows until revealed
 sta COL,x
 sta COL+256,x
 sta COL+512,x
 sta COL+744,x
 sta $5c00,x
 sta $5c00+256,x
 sta $5c00+512,x
 sta $5c00+744,x
 inx
 bne ts_clear
 lda #0
 sta $d020
 sta $d021                   ; %00 pixels = black (raster bars repaint it)
 sta music_pos
 sta music_frame
 sta ip_msb
 ldx #7
ts_sprites:                  ; parade sprites: parked off-screen, MC, black/grey shared colours
 lda #0
 sta ip_st,x
 sta ip_xlo,x
 sta ip_xhi,x
 sta $5ff8,x                 ; pointers: epoch 0 frame 0 until they start walking
 txa
 asl
 tay
 lda #0
 sta $d000,y
 lda #IP_Y
 sta $d001,y
 lda ip_col,x
 sta $d027,x
 dex
 bpl ts_sprites
 lda #0
 sta $d010
 sta $d017
 sta $d01d
 sta $d01b                   ; sprites in front of the bitmap
 sta $d025                   ; MC colour 1: black outlines
 lda #15
 sta $d026                   ; MC colour 2: light grey
 lda #$ff
 sta $d01c
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
 sta music_hold              ; the music waits for the parade
 lda #SMP_ORCH
 jsr sample_play             ; original orchestra hit
title_wait:
 jsr wait_frame
 jsr intro_step
 lda it
 cmp #44
 bcc ts_poll                 ; PRESS FIRE row not revealed yet
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
ts_poll:
 jsr KGETIN
 bne title_done
 lda joy_raw
 and #16
 bne title_wait
title_done:
 jsr sample_stop
 lda #0
 sta title_active
 sta title_bmp
 sta music_hold
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
 ldx #7
ts_rest_sp:                  ; the game's sprite registers back
 lda ts_save,x
 sta $d000,x
 lda ts_save+8,x
 sta $d008,x
 dex
 bpl ts_rest_sp
 lda ts_save+16
 sta $d010
 ldx #9
ts_rest_col:
 lda ts_save+17,x
 sta $d025,x
 dex
 bpl ts_rest_col
 lda ts_save+27
 sta $d017
 lda ts_save+28
 sta $d01b
 lda ts_save+29
 sta $d01c
 lda ts_save+30
 sta $d01d
 lda #3
 sta $d015
 rts

; One intro frame: reveal rows, then move the parade.
intro_step:
 lda it
 cmp #REVEAL_FRAMES
 bcs ip_parade
 and #3
 bne is_inc
 lda it
 lsr
 lsr
 sta rv_k                    ; step 0..12: rows 12-k and 12+k
 lda #12
 sec
 sbc rv_k
 tax
 jsr reveal_row
 lda #12
 clc
 adc rv_k
 tax
 jsr reveal_row
is_inc:
 inc it
 rts

; X = row: copy its screen-RAM colours (from intro_screen_src) and colour-RAM colours.
reveal_row:
 lda crow_lo,x
 sta PTR
 sta CPTR
 lda crow_hi,x
 sec
 sbc #$d8                    ; high byte of row*40
 sta rv_hi
 clc
 adc #>intro_screen_src
 sta PTR+1
 lda rv_hi
 clc
 adc #$5c
 sta CPTR+1
 jsr rv_copy
 lda rv_hi
 clc
 adc #>intro_color
 sta PTR+1
 lda rv_hi
 clc
 adc #>COL
 sta CPTR+1
rv_copy:
 ldy #39
rv_loop:
 lda (PTR),y
 sta (CPTR),y
 dey
 bpl rv_loop
 rts

; Parade: soldier k enters at clock ip_start[k], walks IP_SPEED px/frame to ip_fxlo/hi[k],
; then marches on the spot. Arrival plays that epoch's weapon sample.
ip_parade:
 lda ip_clock
 cmp #255
 beq ip_go
 inc ip_clock
ip_go:
 lda #0
 sta ip_msb
 ldx #7
ip_loop:
 lda ip_clock
 cmp ip_start,x
 bcs ip_entered
 jmp ip_next                 ; not entered yet
ip_entered:
 lda ip_st,x
 cmp #2
 beq ip_pos
 bne ip_walk
ip_walk:
 cmp #0
 bne ip_step
 lda #1
 sta ip_st,x                 ; enters now: switch its sprite on
 lda ip_bit,x
 ora $d015
 sta $d015
ip_step:
 lda ip_xlo,x
 clc
 adc #IP_SPEED
 sta ip_xlo,x
 bcc ip_cmp
 inc ip_xhi,x
ip_cmp:
 lda ip_xhi,x
 cmp ip_fxhi,x
 bcc ip_pos                  ; still left of the slot
 bne ip_land
 lda ip_xlo,x
 cmp ip_fxlo,x
 bcc ip_pos
ip_land:
 lda ip_fxlo,x
 sta ip_xlo,x
 lda ip_fxhi,x
 sta ip_xhi,x
 lda #2
 sta ip_st,x
 stx ip_k
 lda attack_smp,x
 jsr sample_play             ; this epoch's weapon
 ldx ip_k
 inc ip_arrived
 lda ip_arrived
 cmp #8
 bne ip_pos
 lda #1
 sta title_active            ; bars on behind the logo
 lda #0
 sta music_hold              ; and the title tune starts
 sta music_pos
 sta music_frame
ip_pos:
 txa
 asl
 tay
 lda ip_xlo,x
 sta $d000,y
 lda ip_xhi,x
 beq ip_anim
 lda ip_msb
 ora ip_bit,x
 sta ip_msb
ip_anim:
 lda vblank
 lsr
 lsr
 ldy ip_st,x
 cpy #2
 bcc ip_fr
 lsr                         ; marching on the spot is slower
ip_fr:
 stx ip_k
 clc
 adc ip_k
 and #3
 sta rv_k
 txa
 asl
 asl
 ora rv_k
 sta $5ff8,x                 ; epoch k, walk frame (orig_army pointer = epoch*4 + frame)
ip_next:
 dex
 bmi ip_done
 jmp ip_loop
ip_done:
 lda ip_msb
 sta $d010
 rts

ip_start: !byte 0,24,48,72,96,120,144,168
ip_fxlo:  !byte 38,76,114,152,190,228,10,48
ip_fxhi:  !byte 0,0,0,0,0,0,1,1
ip_bit:   !byte 1,2,4,8,16,32,64,128
ip_col:   !byte 10,13,14,7,3,8,4,1
title_pal: !byte 2,10,7,1,7,3,14,6      ; hires-safe cycle for the PRESS FIRE row
