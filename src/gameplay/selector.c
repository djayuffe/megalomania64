/* One-shot launch handoff from the independent scene/island selector. */
#include "game.h"
uint8_t ng_select_island(uint8_t island) {
    uint8_t i;uint16_t pool;
    if(island>=28)return 0;
    ng_state[NG_ISLAND]=island;ng_state[NG_ORDER_EPOCH]=0;
    pool=100+(uint16_t)(island/3)*100;
    if(island==27) {
        /* A standalone final-battle checkpoint has no earlier saved people. */
        pool=100;for(i=0;i<4;++i) {ng_state[NG_RESERVE+i*2]=0xe8;ng_state[NG_RESERVE+i*2+1]=3;}
    }
    ng_state[NG_POOL]=(uint8_t)pool;ng_state[NG_POOL+1]=(uint8_t)(pool>>8);
    ng_state[NG_DEPLOY]=island==27?100:20;ng_state[NG_DEPLOY+1]=0;
    return 1;
}
void ng_selector_start(void) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    volatile uint8_t *p=(uint8_t *)0x02f0;
    uint8_t valid,index,user;index=p[3];user=p[5];
    valid=p[0]=='S' && p[1]=='E' && p[2]=='L' && p[4]==(uint8_t)~index && p[6]==(uint8_t)~user && user<4 && index<28;
    p[0]=0;if(valid && ng_select_island(index)) {
        ng_state[NG_HUMAN]=user;
        ng_state[NG_HOTSEAT]=0;
        ng_state[NG_ACTIVE]=(uint8_t)(1u<<user);
        ng_state[NG_SELECTED]=0;
    }
#endif
}
