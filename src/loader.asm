; Sequential KERNAL channel, bounded RLE output. No NMI may run on the IEC bus.
; ld_open: A=filename length, X/Y=filename. ld_unpack: PTR=destination,
; ld_left=exact output length. Carry set on all errors, including truncated EOF.
ld_open:
 jsr $ffbd
 jsr sample_stop
 jsr get_device
 lda #2
 ldx devnum
 ldy #2
 jsr $ffba
 lda #0
 sta ld_eof
 sta ld_error
 sta ld_opened
 jsr $ffc0
 bcs ld_fail
 ldx #2
 jsr $ffc6
 bcs ld_fail
 lda #1
 sta ld_opened
 clc
 rts
ld_close:
 lda #0
 sta ld_opened
 jsr $ffcc
 lda #2
 jsr $ffc3
 rts
ld_read:
 stx ld_rx
 sty ld_ry
 lda ld_eof
 bne ld_fail_read
 jsr $ffcf
 sta ld_value
 jsr $ffb7
 sta ld_status
 and #$bf
 bne ld_fail_read
 lda ld_status
 and #$40
 sta ld_eof
 jsr intro_poll
 bcs ld_fail_read
 ldx ld_rx
 ldy ld_ry
 lda ld_value
 clc
 rts
ld_fail_read:
 ldx ld_rx
 ldy ld_ry
ld_fail:
 lda #1
 sta ld_error
 sec
 rts
ld_unpack:
 lda ld_left
 ora ld_left+1
 beq ld_unpacked
 jsr ld_read
 bcs ld_unpack_bad
 bmi ld_run
 tax
 inx
 stx ld_count
ld_literal:
 jsr ld_read
 bcs ld_unpack_bad
 jsr ld_put
 bcs ld_unpack_bad
 dec ld_count
 bne ld_literal
 jmp ld_unpack
ld_run:
 and #$7f
 clc
 adc #3
 sta ld_count
 jsr ld_read
 bcs ld_unpack_bad
 sta ld_repeat
ld_run_byte:
 lda ld_repeat
 jsr ld_put
 bcs ld_unpack_bad
 dec ld_count
 bne ld_run_byte
 jmp ld_unpack
ld_unpacked:
 clc
 rts
ld_unpack_bad:
 sec
 rts
ld_put:
 pha
 lda ld_left
 ora ld_left+1
 beq ld_put_bad
 pla
 sta ld_write
 php
 sei
 lda $01
 pha
 and #$f8
 sta $01                     ; one bounded write, including RAM beneath I/O
 lda ld_write
 ldy #0
 sta (PTR),y
 pla
 sta $01
 plp
 inc PTR
 bne ld_put_count
 inc PTR+1
ld_put_count:
 lda ld_left
 bne ld_put_low
 dec ld_left+1
ld_put_low:
 dec ld_left
 clc
 rts
ld_put_bad:
 pla
 jmp ld_fail
