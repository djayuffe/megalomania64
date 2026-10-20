; Optional full-length original effects replace the clipped fallback bank.
; $D400-$DFFF is RAM beneath SID/I/O, read only during NMI sample fetches.
effects_load:
 lda #7
 ldx #<fx_name
 ldy #>fx_name
 jsr ld_open
 bcs fx_load_done
 ldx #0
fx_header:
 jsr ld_read
 bcs fx_load_done
 cmp fx_magic,x
 bne fx_load_done
 inx
 cpx #4
 bcc fx_header
 lda #0
 sta fx_valid                 ; a partially overwritten bank must never be played
 lda #<smp_data
 sta PTR
 lda #>smp_data
 sta PTR+1
 lda #$28
 sta ld_left
 lda #$23
 sta ld_left+1                ; 9000 bytes in the padded fallback region
 jsr ld_unpack
 bcs fx_load_done
 lda #0
 sta PTR
 sta ld_left
 lda #$d4
 sta PTR+1
 lda #$0c
 sta ld_left+1
 jsr ld_unpack
 bcs fx_load_done
 lda ld_eof
 beq fx_load_done
 lda #1
 sta fx_ready
 sta fx_valid
fx_load_done:
 jmp ld_close
 effects_code_end:
