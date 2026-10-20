; A 320x600 credit card is represented by a deduplicated hires character set,
; 75 rows of characters and 75 rows of cell colours. The lower 40 pixels use
; a fixed bitmap logo. No game state or original sprite-source RAM is replaced.
credit_load_segments:
 ldx ic_segment
 lda cr_dest_lo,x
 sta PTR
 lda cr_dest_hi,x
 sta PTR+1
 lda cr_size_lo,x
 sta ld_left
 lda cr_size_hi,x
 sta ld_left+1
 jsr ld_unpack
 lbcs ic_load_bad
 inc ic_segment
 lda ic_segment
 cmp #5
 bcc credit_load_segments
 lda ld_eof
 lbeq ic_load_bad
 jsr ld_close
 clc
 rts

credit_flip:
 lda #$0b
 sta $d011
 jsr credit_logo_copy
 lda #0
 sta cr_phase
 sta cr_row
 sta cr_ptr
 sta $d020
 sta $d021
 lda #$58
 sta cr_ptr+1
 lda #3
 sta cr_y
 jsr credit_rows
 lda $dd00
 and #$fc
 sta $dd00
 lda #$38
 sta $d018
 lda #8
 sta $d016
 lda #3
 sta ic_visible_mode
 lda #$1b
 sta $d011
 jmp ic_displayed

credit_tick:
 lda ic_hold+1
 bne cr_advance
 lda ic_hold
 cmp #2
 bcc cr_done
cr_advance:
 inc cr_phase
 lda cr_phase
 and #7
 sta cr_phase
 bne cr_fine
 inc cr_row
 ; source row advances by forty cells every eight pixels
 clc
 lda cr_ptr
 adc #40
 sta cr_ptr
 bcc cr_update
 inc cr_ptr+1
cr_update:
 jsr credit_rows
cr_fine:
 lda #3
 sec
 sbc cr_phase
 and #7
 sta cr_y
cr_done:
 rts

; Patch eight absolute indexed source operands once per coarse scroll. Four
; 200-byte stripes copy exactly the 800 visible cells, preserving logo cells.
credit_rows:
 lda cr_ptr
 sta cr_chars0+1
 clc
 adc #200
 sta cr_chars1+1
 lda cr_ptr
 clc
 adc #144
 sta cr_chars2+1
 lda cr_ptr
 clc
 adc #88
 sta cr_chars3+1
 lda cr_ptr+1
 sta cr_chars0+2
 lda cr_ptr
 clc
 adc #200
 lda cr_ptr+1
 adc #0
 sta cr_chars1+2
 lda cr_ptr
 clc
 adc #144
 lda cr_ptr+1
 adc #1
 sta cr_chars2+2
 lda cr_ptr
 clc
 adc #88
 lda cr_ptr+1
 adc #2
 sta cr_chars3+2
 ; colour map is $0bb8 bytes beyond the character map
 clc
 lda cr_ptr
 adc #$b8
 sta cr_colors0+1
 lda cr_ptr+1
 adc #$0b
 sta cr_colors0+2
 lda cr_colors0+1
 clc
 adc #200
 sta cr_colors1+1
 lda cr_colors0+2
 adc #0
 sta cr_colors1+2
 lda cr_colors1+1
 clc
 adc #200
 sta cr_colors2+1
 lda cr_colors1+2
 adc #0
 sta cr_colors2+2
 lda cr_colors2+1
 clc
 adc #200
 sta cr_colors3+1
 lda cr_colors2+2
 adc #0
 sta cr_colors3+2
 ldx #199
cr_copy:
cr_chars0:
 lda $5800,x
 sta $cc00,x
cr_chars1:
 lda $58c8,x
 sta $ccc8,x
cr_chars2:
 lda $5990,x
 sta $cd90,x
cr_chars3:
 lda $5a58,x
 sta $ce58,x
cr_colors0:
 lda $63b8,x
 sta $d800,x
cr_colors1:
 lda $6480,x
 sta $d8c8,x
cr_colors2:
 lda $6548,x
 sta $d990,x
cr_colors3:
 lda $6610,x
 sta $da58,x
 dex
 cpx #$ff
 lbne cr_copy
 rts
