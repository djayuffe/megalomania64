* = $0801
!byte $0b,$08,$0a,$00,$9e,$32,$30,$36,$31,$00,$00,$00
* = $080d
 sei
 cld
 ldx #$ff
 txs
 lda #$31
 sta $0314
 lda #$ea
 sta $0315
 lda #0
 sta $d01a
 sta $d015
 lda #$7f
 sta $dd0d
 lda #$81
 sta $dc0d
 lda #$0b
 sta $d011
 cli
 lda #0
 sta boot_index
boot_next:
 ldx boot_index
 lda boot_len,x
 ldy boot_hi,x
 pha
 lda boot_lo,x
 tax
 pla
 jsr $ffbd
 lda #1
 ldx $ba
 cpx #8
 bcs boot_device
 ldx #8
boot_device:
 ldy #1
 jsr $ffba
 lda #0
 jsr $ffd5
 bcs boot_error
 inc boot_index
 lda boot_index
 cmp #6
 bcc boot_next
 jmp $2700
boot_error:
 lda #2
 sta $d020
 jmp boot_error
boot_index: !byte 0
boot_len: !byte 6,5,6,7,6,6
boot_lo: !byte <boot_supp,<boot_low,<boot_high,<boot_extra,<boot_draw,<boot_text
boot_hi: !byte >boot_supp,>boot_low,>boot_high,>boot_extra,>boot_draw,>boot_text
boot_supp: !text "NGSUPP"
boot_low: !text "NGLOW"
boot_high: !text "NGHIGH"
boot_extra:!text "NGEXTRA"
boot_draw: !text "NGDRAW"
boot_text: !text "NGTEXT"
