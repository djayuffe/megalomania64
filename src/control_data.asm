; Streaming control data in otherwise unused bank-0 RAM.

; loader
ld_opened: !byte 0
ld_left: !word 0
ld_eof: !byte 0
ld_error: !byte 0
ld_status: !byte 0
ld_value: !byte 0
ld_rx: !byte 0
ld_ry: !byte 0
ld_count: !byte 0
ld_repeat: !byte 0

; intro
ic_signature: !text "MLI1"
ic_name: !text "SCENE01"
ic_title: !text "TITLE"
ic_dest_lo: !byte $00,$00,$00,$00,$00,$00
ic_dest_hi: !byte $60,$5c,$c4,$e0,$cc,$c8
ic_size_lo: !byte $40,$e8,$e8
ic_size_hi: !byte $1f,$03,$03
ic_color_hi: !byte $c4,$c8
ic_vic: !byte 2,0
ic_d018: !byte $78,$38
ic_active: !byte 0
ic_skip: !byte 0
ic_dirty: !byte 0
ic_visible: !byte 0
ic_index: !byte 0
ic_bank: !byte 0
ic_segment: !byte 0
ic_mode: !byte 0
ic_bg: !byte 0
ic_time: !word 0
ic_hold: !word 0
ic_vb: !byte 0
ic_sprites: !byte 0

; speech
sp_sprites: !byte 0
sp_msg: !text "LOADING ORIGINAL VOICES",0
sp_magic: !text "MLV1"
sp_name: !text "SPEECH"
sp_event: !byte $ff,$ff,$ff,0,1,2,$ff,$ff,$ff,$ff,7,6,$ff
sp_index: !fill 32,0
sp_end: !word 0
sp_bytes: !word 0
sp_oldhi: !byte 0
sp_ready: !byte 0
sp_id: !byte 0
sp_wanted: !byte 0
sp_queue: !byte $ff
smp_speech: !byte 0

; level
lc_caption: !text "ENTERING ISLAND",0
lc_epoch: !text "EPOCH",0
lc_magic: !text "MLC1"
lc_name: !text "ISL01"
lc_regs: !byte $10,$15,$17,$1c,$1d,$25,$26,$2b,$2c
lc_saved: !fill 9,0
lc_pos: !fill 4,0
lc_ptr: !word 0
lc_colors: !fill 3,0
lc_ok: !byte 0
cards_on: !byte 0

nmi_busy: !byte 0
control_data_end:
