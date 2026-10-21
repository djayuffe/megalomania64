.export gp_run
.import _gp_dispatch
.importzp c_sp
.segment "STARTUP"
gp_run:
    lda #$ff
    sta c_sp
    lda #$c3
    sta c_sp+1
    jsr _gp_dispatch
    rts
