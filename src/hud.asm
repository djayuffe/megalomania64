; --------------------------------------------------------------------------
; HUD colour pass. Text is printed in white; this recolours whole rows/segments
; of colour RAM after every score/panel redraw so labels, factions and help
; read at a glance. Also the per-epoch border colour.
; --------------------------------------------------------------------------
; A = colour, X = row, Y = first column, cu_len = count
fill_colour:
 pha
 lda crow_lo,x
 sta fc_st+1
 lda crow_hi,x
 sta fc_st+2
 pla
 ldx cu_len
fc_loop:
fc_st:
 sta COL,y
 iny
 dex
 bne fc_loop
 rts

colorize_ui:
 pha
 txa
 pha
 tya
 pha
 ldx #0                       ; segment table: row, first col, length, colour
cu_seg:
 lda hud_seg,x
 bmi cu_panel
 pha
 lda hud_seg+2,x
 sta cu_len
 lda hud_seg+3,x
 sta cu_col
 ldy hud_seg+1,x
 pla
 stx cu_x
 tax
 lda cu_col
 jsr fill_colour
 lda cu_x
 clc
 adc #4
 tax
 jmp cu_seg
cu_panel:
 ldx #3                       ; sidebar rows 3..21, columns 30..39
cu_row:
 lda hud_rowcol,x
 beq cu_next
 stx cu_x
 ldy selected
 cpx #5
 bne cu_plain
 ldy selected                 ; row 5 (OWNER) takes the owner's faction colour
 lda owner,y
 tay
 lda own_col,y
cu_plain:
 ldy #30
 pha
 lda #10
 sta cu_len
 pla
 jsr fill_colour
 ldx cu_x
cu_next:
 inx
 cpx #22
 bne cu_row
 pla
 tay
 pla
 tax
 pla
 rts

set_border:                    ; per-epoch frame colour + epoch sprites (preserves A, X, Y)
 jsr orig_load_epoch
 pha
 tya
 pha
 ldy epoch
 lda border_tab,y
 sta border_col
 sta $d020
 pla
 tay
 pla
 rts

;              row,col,len,colour     -- text colours must be 0-7: 8-15 make glyphs multicolour
hud_seg:   !byte 0, 0,16, 7
           !byte 0,16,17, 3
           !byte 0,33, 7, 1
           !byte 1, 0,11, 5
           !byte 1,12, 7, 7
           !byte 1,21, 8, 7
           !byte 1,30,10, 3
           !byte 22,0,40, 5
           !byte 23,0,40, 3
           !byte 24,0,40, 7
           !byte $ff,0,0,0
;                 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21
hud_rowcol: !byte 0, 0, 0, 3, 0, 1, 7, 1, 0, 7, 0, 5, 1, 3, 7, 5, 5, 5, 0, 1, 3, 7
own_col:   !byte 1,5,7,3,4
border_tab: !byte 6,5,9,11,2,11,12,4,0,14
