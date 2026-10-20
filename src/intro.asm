ic_load:
 jsr ld_open
 lbcs ic_load_bad
 ldx #0
ic_magic:
 jsr ld_read
 lbcs ic_load_bad
 cmp ic_signature,x
 lbne ic_load_bad
 inx
 cpx #4
 bcc ic_magic
 jsr ld_read
 lbcs ic_load_bad
 cmp #5
 lbcs ic_load_bad
 sta ic_mode
 jsr ld_read
 lbcs ic_load_bad
 cmp #16
 lbcs ic_load_bad
 sta ic_bg
 jsr ld_read
 lbcs ic_load_bad
 sta ic_time
 jsr ld_read
 lbcs ic_load_bad
 sta ic_time+1
 ora ic_time
 lbeq ic_load_bad
 lda ic_mode
 cmp #3
 bne ic_header_ok
 lda ic_time+1
 cmp #2
 lbcs ic_load_bad
 cmp #1
 bne ic_header_ok
 lda ic_time
 cmp #145
 lbcs ic_load_bad
ic_header_ok:
 lda #0
 sta ic_segment
 lda ic_bank
 bne ic_segments
 lda #1
 sta ic_dirty                 ; even a failed unpack may overwrite the embedded bitmap
ic_segments:
 lda ic_mode
 cmp #4
 beq ic_patch_segments
 lda ic_mode
 cmp #3
 bne ic_bitmap_segments
 jmp credit_load_segments
ic_patch_segments:
 ldx ic_segment
 lda ic_patch_lo,x
 sta PTR
 lda ic_patch_hi,x
 sta PTR+1
 lda ic_patch_size_lo,x
 sta ld_left
 lda ic_patch_size_hi,x
 sta ld_left+1
 jmp ic_unpack_segment
ic_bitmap_segments:
 lda ic_bank
 asl
 clc
 adc ic_bank
 clc
 adc ic_segment
 tax
 lda ic_dest_lo,x
 sta PTR
 lda ic_dest_hi,x
 sta PTR+1
 ldx ic_segment
 lda ic_size_lo,x
 sta ld_left
 lda ic_size_hi,x
 sta ld_left+1
 ic_unpack_segment:
 jsr ld_unpack
 bcs ic_load_bad
 inc ic_segment
 lda ic_segment
 cmp #3
 bcc ic_segments
 lda ld_eof
 beq ic_load_bad              ; reject trailing bytes, not just a valid prefix
 jsr ld_close
 clc
 rts
ic_load_bad:
 jsr ld_close
 lda ic_visible
 beq ic_no_skip
 lda #1
 sta ic_skip
ic_no_skip:
 sec
 rts

ic_flip:
 lda ic_mode
 cmp #3
 bne ic_bitmap_flip
 jmp credit_flip
ic_bitmap_flip:
 lda #$0b
 sta $d011
 ldx ic_bank
 lda ic_color_hi,x
 sta PTR+1
 lda #0
 sta PTR
 sta CPTR
 lda #$d8
 sta CPTR+1
 ldx #4
 ldy #0
ic_colors:
 lda (PTR),y
 sta (CPTR),y
 iny
 bne ic_colors
 inc PTR+1
 inc CPTR+1
 dex
 bne ic_colors
 ldx ic_bank
 lda $dd00
 and #$fc
 ora ic_vic,x
 sta $dd00
 lda ic_d018,x
 sta $d018
 lda ic_mode
 cmp #4
 bne ic_flip_mode
 lda #2
ic_flip_mode:
 sta ic_visible_mode
 cmp #0
 beq ic_hires
 lda #$18
 bne ic_d016
ic_hires:
 lda #$08
ic_d016:
 sta $d016
 lda ic_bg
 sta $d021
 lda #0
 sta $d020
 lda #$3b
 sta $d011
ic_displayed:
 rts
