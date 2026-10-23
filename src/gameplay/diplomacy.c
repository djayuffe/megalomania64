/* DOS 16B4:2A84 negotiation state machine. Leaf bank; no nested disk loads.
 * The first 30 state bytes retain DS:19AA..19C7 exactly. Last two bytes
 * describe the speech event for the native interface and audit callback. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("DIPLOMACY")
#pragma rodata-name ("DIPLOMACY")
#endif
static uint16_t r(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void w(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static uint16_t draw(uint16_t bound) {gp_request[0]=7;w(gp_request+2,bound);gp_dispatch();return r(gp_request+12);}
static void willingness(uint8_t *d,uint8_t bit) {
    if(draw(100)<r(gp_personality+0x34))d[28]|=bit;else d[28]&=(uint8_t)~bit;
}
static void leave(uint8_t f) {
    uint8_t i,bit;bit=1<<f;if(gp_alliances[f]==bit)return;
    for(i=0;i<4;++i)gp_alliances[i]&=(uint8_t)~bit;gp_alliances[f]=bit;
    w(gp_request+16,r(gp_request+16)+1);
}
static void join(uint8_t a,uint8_t b) {
    uint8_t i,mask;if(a==b || (gp_alliances[a]&(1<<b)))return;
    mask=gp_alliances[a]|gp_alliances[b];
    for(i=0;i<4;++i)if(mask&(1<<i))gp_alliances[i]|=mask;
    w(gp_request+16,r(gp_request+16)-1);
}
static void close_proposal(uint8_t *d) {uint8_t i;for(i=4;i<16;++i)d[i]=0;}
static void begin(uint8_t *d,uint8_t f,uint8_t target,uint8_t active) {
    w(d,f);w(d+4,1);w(d+6,0);w(d+8,0);w(d+10,0);w(d+12,0);w(d+14,0);w(d+16,1);
    d[19]=gp_alliances[target];d[18]=(gp_alliances[f]|d[19])&active&~(1<<f);
}
static void say(uint8_t *d,uint8_t f,uint8_t kind) {
    static const uint8_t base[4]={8,22,79,15};
    d[30]=base[f]+kind;d[31]=f;w(d+16,0);gp_request[24]=1;
}
/* request: faction word2, accept word4, reject word6, clock word14,
 * presentation mode word16, demo word18, human word26, active byte30.
 * Seed word10 and presentation mode are updated. Word22 marks consumed input. */
void gp_diplomacy_tick(uint8_t *d) {
    uint8_t f,bit,active,h,demo,oldmask,candidates[4],n,i,target,accept,reject;
    uint16_t interval,clock,init;
    f=(uint8_t)r(gp_request+2);if(f>=4)return;bit=1<<f;active=gp_request[30];h=gp_request[26];demo=(uint8_t)r(gp_request+18);
    accept=(uint8_t)r(gp_request+4);reject=(uint8_t)r(gp_request+6);clock=r(gp_request+14);w(gp_request+22,0);gp_request[24]=0;
    if(d[29]&bit) {d[29]&=(uint8_t)~bit;willingness(d,bit);}
    interval=r(gp_personality+0x30)*10;
    if(r(gp_personality+0x30) && (uint16_t)(clock-r(d+20+(uint16_t)f*2))>=interval) {
        w(d+20+(uint16_t)f*2,r(d+20+(uint16_t)f*2)+interval);willingness(d,bit);
        if(r(d+4) || (!demo && f==h))goto pending;
        oldmask=0;
        if(draw(100)<r(gp_personality+0x36) && gp_alliances[f]!=bit) {oldmask=gp_alliances[f];leave(f);}
        if(draw(100)>=r(gp_personality+0x32) || (gp_alliances[f]&(1<<h)))return;
        n=0;i=4;while(i) {--i;if(i!=f && (active&(1<<i)) && !(gp_alliances[f]&(1<<i)))candidates[n++]=i;}
        if(!n)return;target=candidates[draw(n)];if((oldmask&(1<<target)) || r(gp_request+16)==2)return;
        begin(d,f,target,active);return;
    }
pending:
    if(!r(d+4) || !r(d+16))return;
    if(r(d+12))goto closed;
    if(!d[18])goto completed;
    init=r(d);if(init>=4 || !(active&(1<<init)))goto closed;
    if(!(d[18]&bit))return;
    if(!(active&bit))goto closed;
    if(!demo && f==h) {
        if(d[18]&active&~bit)return;
        if(!r(d+8)) {w(d+10,1);w(d+14,1);say(d,(uint8_t)init,0);w(d+8,1);return;}
        if(!r(d+6)) {w(d+6,1);return;}
        if(r(gp_request+16)==2) {w(d+6,0);goto closed;}
        if(accept) {w(d+6,0);w(gp_request+22,1);goto accepted;}
        if(reject) {w(d+6,0);w(gp_request+22,1);goto closed;}
        return;
    }
    if(!(d[28]&bit)) {
        if(!demo && init==h) {w(d+12,1);w(d+14,1);say(d,f,2);return;}
        goto closed;
    }
accepted:
    d[18]&=(uint8_t)~bit;if(d[18])return;
    if(!demo && r(d)==h) {
        n=d[19]&active;if(!n)goto closed;
        do {target=(uint8_t)draw(4);}while(!(n&(1<<target)));
        w(d+14,1);say(d,target,1);return;
    }
completed:
    init=r(d);if(init>=4)goto closed;
    if(r(gp_request+16)!=2 && !(d[19]&(1<<init))) {
        for(i=0;i<4 && !(d[19]&(1<<i));++i) {}if(i<4)join((uint8_t)init,i);
    }
    d[28]&=(uint8_t)~(gp_alliances[init]&~(1<<init));
closed:
    close_proposal(d);
}

static uint8_t *state(void) {return ng_state+NG_DIPLO;}
static void initialize(void) {
    uint8_t i,*d;d=state();
    if(ng_state[NG_DIP_TAG]!=NG_DIP_REVISION) {
        for(i=0;i<32;++i)d[i]=0;ng_state[NG_DIP_TAG]=NG_DIP_REVISION;
        w(d,65535);w(d+16,1);d[29]=ng_state[NG_ACTIVE];
        for(i=0;i<4;++i)w(d+20+(uint16_t)i*2,r(ng_state+NG_CLOCK));
    }
}
void ng_diplomacy_initialize(void) {initialize();}
static void personality(uint8_t f) {
    uint8_t i,k,kind;kind=0;
    if(f==ng_state[NG_HUMAN])kind=3;
    else for(i=0;i<4;++i) {k=i==1?2:i==2?1:i;if(k==ng_state[NG_HUMAN])continue;if(k==f)break;++kind;}
    for(i=0;i<56;++i)gp_personality[i]=world_personalities[(uint16_t)kind*56+i];
}
#if defined(__CC65__) && defined(NATIVE_GAME)
extern uint8_t hw_audio_busy(void);
#else
#define hw_audio_busy() 0
#endif
void ng_diplomacy_advance(void) {
    uint8_t f,*d;uint16_t seed,mode;initialize();d=state();
    if(!r(d+16) && !hw_audio_busy() && !(ng_event&32))w(d+16,1);
    seed=r(ng_state+NG_SEED);mode=0;f=4;
    while(f) {
        --f;personality(f);
        /* Hotseat's other factions are controlled by people: proposals are
         * manual and their group consent is explicit in that shared mode. */
        if(ng_state[NG_HOTSEAT]) {w(gp_personality+0x30,0);d[28]|=ng_state[NG_ACTIVE];d[29]=0;}
        w(gp_request+2,f);w(gp_request+4,f==ng_state[NG_HUMAN]?d[2]:0);w(gp_request+6,f==ng_state[NG_HUMAN]?d[3]:0);
        w(gp_request+10,seed);w(gp_request+14,r(ng_state+NG_CLOCK));w(gp_request+16,mode);w(gp_request+18,0);
        w(gp_request+26,ng_state[NG_HUMAN]);w(gp_request+30,ng_state[NG_ACTIVE]);gp_diplomacy_tick(d);
        seed=r(gp_request+10);mode=r(gp_request+16);
        if(r(gp_request+22))d[2]=d[3]=0;
        if(gp_request[24])ng_event|=32;
    }
    if(!r(d+4))d[2]=d[3]=0;
    w(ng_state+NG_SEED,seed);for(f=0;f<4;++f)ng_state[NG_ALLIES+f]=gp_alliances[f];
}
void ng_diplomacy_propose(uint8_t other) {
    uint8_t *d,h;initialize();d=state();h=ng_state[NG_HUMAN];
    if(other>=4 || other==h || !(ng_state[NG_ACTIVE]&(1<<other)) || (gp_alliances[h]&(1<<other)) || r(d+4))return;
    begin(d,h,other,ng_state[NG_ACTIVE]);d[2]=d[3]=0;ng_diplomacy_advance();
}
void ng_diplomacy_reply(uint8_t yes) {
    uint8_t *d;d=state();if(!r(d+4) || !r(d+6))return;
    d[2]=yes!=0;d[3]=yes==0;ng_diplomacy_advance();
}
