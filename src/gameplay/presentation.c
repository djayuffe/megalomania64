/* Dialogue presentation leaf overlay. Original face/voice assets stay on disk. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("PRESENTATION")
#pragma rodata-name ("PRESENTATION")
#endif
extern uint8_t __fastcall__ hw_open(const char *name);
extern uint8_t hw_read(void),hw_error;
extern void hw_close(void);
extern uint8_t unpack(uint8_t *dest,uint16_t left);
extern void text(uint16_t at,const char *s,uint8_t ink);
#define REG(a) (*(volatile uint8_t *)(a))
uint8_t ng_face_owner=255;
static uint8_t face_inks[16];
/* hw_open exposes KERNAL before scanning the name; keep it outside EF00. */
static char face_file[7]="NFAC00";
uint8_t ng_dialogue_voice(void) {
    static const uint8_t bases[4]={8,22,79,15};
    uint8_t speaker,id;
    speaker=ng_state[NG_DIPLO+31];id=ng_state[NG_DIPLO+30];
    if(speaker>=4 || id<bases[speaker] || id>=bases[speaker]+3)return 255;
    return 20+speaker*3+id-bases[speaker];
}
void ng_dialogue_draw(void) {
    static const char *const names[4]={"FACTION 1","FACTION 2","FACTION 3","FACTION 4"};
    uint8_t speaker,i,j,bank,ok;uint16_t at;
    speaker=ng_state[NG_DIPLO+31];if(speaker>=4)return;
    if(ng_face_owner!=speaker) {
        ng_face_owner=255;
        face_file[5]='0'+speaker;
        if(!hw_open(face_file))return;
        ok=hw_read()=='N' && hw_read()=='G' && hw_read()=='H' && hw_read()=='1';
        ok=ok && unpack((uint8_t *)0x3f80,128);
        if(ok)for(i=0;i<16;++i)face_inks[i]=hw_read();
        ok=ok && !hw_error;hw_close();if(!ok)return;
        ng_face_owner=speaker;
    }
    bank=REG(1);REG(1)=0x35;
    for(i=0;i<6;++i)for(j=0;j<15;++j) {
        at=385+(uint16_t)i*40+j;REG(0x0400+at)=32;REG(0xd800+at)=1;
    }
    for(i=0;i<16;++i) {
        at=425+(uint16_t)(i/4)*40+i%4;
        REG(0x0400+at)=240+i;REG(0xd800+at)=face_inks[i];
    }
    text(385,names[speaker],7);REG(1)=bank;
}
