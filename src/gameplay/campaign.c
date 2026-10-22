/* Campaign menu overlay: data-only policy, never calls another disk overlay.
 * DOS CS0:1835/7205 supplies three-island epochs and +100 unspent men per
 * epoch. CS0:6B6C supplies saved people; the last battle uses saved/10 men. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("CAMPAIGN")
#endif
static uint16_t r(uint8_t at) {return ng_state[at]|((uint16_t)ng_state[at+1]<<8);}
static void w(uint8_t at,uint16_t n) {ng_state[at]=(uint8_t)n;ng_state[at+1]=(uint8_t)(n>>8);}
static uint8_t done(uint8_t i) {return ng_state[NG_DONE+i/8]&(1<<(i%8));}
uint8_t ng_campaign_action(uint8_t key) {
    uint8_t i,epoch,base,choice,h;uint16_t pool,n;
    h=ng_state[NG_HUMAN];pool=r(NG_POOL);choice=ng_state[NG_ISLAND];epoch=choice/3;base=epoch*3;
    if(ng_state[NG_STATUS]==NG_WON && key=='N') {
        ng_state[NG_DONE+choice/8]|=1<<(choice%8);
        for(i=base;i<base+3 && done(i);++i) {}
        if(i==base+3) {
            base+=3;pool=base==27?r(NG_RESERVE+(uint8_t)(h*2))/10:pool+100;
            w(NG_POOL,pool);i=base;
        }
        ng_state[NG_ISLAND]=i;ng_state[NG_STATUS]=NG_PLAYING;
        ng_state[NG_PHASE]=1;ng_state[NG_PAUSED]=1;ng_state[NG_WITHDRAW]=0;
        w(NG_DEPLOY,i==27?pool:(pool<20?pool:20));
        if(!pool) {ng_state[NG_STATUS]=NG_LOST;ng_state[NG_PHASE]=0;}return 1;
    }
    if(!ng_state[NG_PHASE])return 0;
    n=r(NG_DEPLOY);
    if(choice<27 && key=='+' && n<pool) {n+=10;w(NG_DEPLOY,n>pool?pool:n);return 2;}
    if(choice<27 && key=='-' && n>1) {w(NG_DEPLOY,n>10?n-10:1);return 2;}
    if(key=='N' && choice<27) {
        for(i=0;i<3;++i) {choice=base+(choice-base+1)%3;if(!done(choice))break;}
        ng_state[NG_ISLAND]=choice;return 1;
    }
    if(key==13 && n && n<=pool && ng_terrain[ng_state[NG_SELECTED]]) {
        ng_state[NG_START]=ng_state[NG_SELECTED];w(NG_POOL,pool-n);
        ng_state[NG_PHASE]=0;ng_state[NG_PAUSED]=0;return 1;
    }
    return 0;
}
