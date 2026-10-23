/* Original tactical army turns. Leaf plans return before military bank loads. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("BATTLE")
#endif
static uint16_t r(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void w(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static void get(uint8_t s) {world_slot=s;world_get();}
static uint16_t draw(uint16_t bound) {ng_rule(7,bound,0,0);return r(gp_request+12);}
#ifdef __CC65__
#pragma code-name ("STRATEGY")
#endif
static uint16_t percent(uint16_t p,uint16_t n) {return (uint16_t)((uint16_t)(p*n)+99)/100;}
static uint8_t hostile(uint8_t s,uint8_t f) {
    uint8_t i,found,owner;owner=ng_owners[s];found=0;
    if(owner<4 && !(gp_alliances[f]&(1<<owner)))return 1;
    for(i=0;i<4;++i)if((ng_state[NG_ACTIVE]&(1<<i)) && ng_units[s][i]) {
        if(!(gp_alliances[f]&(1<<i)))return 1;found=1;
    }
    return owner==4 && !found;
}
static void balance(uint8_t s,uint8_t f,uint16_t *allied,uint16_t *enemy) {
    uint8_t i;*allied=0;*enemy=0;
    for(i=0;i<4;++i)if(ng_state[NG_ACTIVE]&(1<<i)) {
        if(gp_alliances[f]&(1<<i))*allied+=ng_strength[s][i];else *enemy+=ng_strength[s][i];
    }
}
/* 16B4:114F, 28A3, 2974: uniform ascending-sector candidates, air
 * attempt then ground retry; native coordinator supplies the single chance draw. */
void ng_expedition_plan(uint8_t air,uint16_t reachable) {
    uint8_t candidates[16],n,i,s,f,target,age;uint16_t allied,enemy,need,people,free;
    s=world_slot;f=(uint8_t)r(gp_sector+0x3fe);gp_plan[0]=255;if(f>=4)return;
    free=r(gp_sector+GP_FREE);n=0;
    for(i=0;i<16;++i)if(i!=s && ng_terrain[i] && !ng_ruined[i] && hostile(i,f) && (air || (reachable&((uint16_t)1<<i))))candidates[n++]=i;
    if(!n)return;target=candidates[draw(n)];balance(target,f,&allied,&enemy);
    need=draw(r(gp_personality+0x1c)-r(gp_personality+0x1a)+1)+r(gp_personality+0x1a);
    if(!enemy && !allied)need=1;
    else {need=percent(need,enemy);if(allied>=need)return;need-=allied;}
    age=10;if(!(reachable&((uint16_t)1<<target)))age=6;
    else if(ng_owners[target]!=4 && ng_state[NG_ISLAND]!=27 && !enemy)age=0;
    people=draw(r(gp_personality+0x20)-r(gp_personality+0x1e)+1)+r(gp_personality+0x1e);
    if(age==6)people/=2;else if(free>=100)people=(uint16_t)(people*free)/100;
    gp_plan[0]=target;w(gp_plan+2,need);w(gp_plan+4,people);gp_plan[6]=age;
    w(gp_plan+8,ng_owners[target]<4 && (gp_alliances[f]&(1<<ng_owners[target]))?65535:8);
}
/* Personality assignment in CS0:72C0, shared by home and roaming turns. */
void ng_personality(uint8_t f) {
    uint8_t i,cat,kind;kind=0;
    if(f==ng_state[NG_HUMAN])kind=3;
    else for(i=0;i<4;++i) {cat=i==1?2:i==2?1:i;if(cat==ng_state[NG_HUMAN])continue;if(cat==f)break;++kind;}
    for(i=0;i<56;++i)gp_personality[i]=world_personalities[(uint16_t)kind*56+i];
}
/* 16B4:0228 first phase: select an active army before checking its
 * eligibility. Rejected selections still consume the original random draw. */
static uint8_t roaming_faction(uint8_t sos) {
    uint8_t choices[4],n,f,i,s,owner;uint16_t allied,enemy;
    s=world_slot;owner=ng_owners[s];n=0;i=4;
    while(i) {--i;if((ng_state[NG_ACTIVE]&(1<<i)) && ng_units[s][i])choices[n++]=i;}
    if(!n)return 255;f=choices[draw(n)];if(f==ng_state[NG_HUMAN])return 255;
    if(f==owner) {if(!sos)return 255;}
    else {
        if(owner<4 && !(gp_alliances[f]&(1<<owner))) {
            if(ng_state[NG_ISLAND]==27 || gp_sector[0x2c8+(uint16_t)f*11+10]!=ng_units[s][f])return 255;
            balance(s,f,&allied,&enemy);if(enemy)return 255;
        }
        for(i=0;i<4;++i)if(i!=f && (ng_state[NG_ACTIVE]&(1<<i)) && ng_units[s][i] && !(gp_alliances[f]&(1<<i)))return 255;
    }
    ng_personality(f);if(draw(100)>=r(gp_personality+0x28))return 255;
    gp_plan[10]=0;for(i=6;i<10;++i)if(gp_sector[0x2c8+(uint16_t)f*11+i])gp_plan[10]=1;
    return f;
}
/* 08 90 / 09 61 include self-owned or hostile/empty territory. */
static void roaming_plan(uint8_t f,uint16_t reachable) {
    uint8_t candidates[16],n,i,s,target,owner;uint16_t allied,enemy,threshold,power;
    s=world_slot;n=0;gp_plan[0]=255;
    for(i=0;i<16;++i)if(i!=s && ng_terrain[i] && !ng_ruined[i] && (reachable&((uint16_t)1<<i)) && (ng_owners[i]==f || hostile(i,f)))candidates[n++]=i;
    if(!n)return;target=candidates[draw(n)];balance(target,f,&allied,&enemy);
    threshold=draw(r(gp_personality+0x2c)-r(gp_personality+0x2a)+1)+r(gp_personality+0x2a);
    if(enemy) {
        threshold=percent(threshold,enemy);if(allied>=threshold)return;
        power=0;for(i=0;i<11;++i)power+=r(gp_sector+0x360+(uint16_t)f*22+(uint16_t)i*2);
        if((uint16_t)(allied+power)<threshold && ng_owners[target]!=f)return;
    }
    owner=ng_owners[target];
    if(ng_state[NG_ISLAND]!=27 && owner<4 && owner!=f && !(gp_alliances[f]&(1<<owner)) && !enemy && gp_sector[0x2c8+(uint16_t)f*11+10]==ng_units[s][f])return;
    gp_plan[0]=target;
}
/* 16B4:0FB2 and 142A: return a weak home army, or demobilize a
 * personality-selected share after no expedition was formed. */
static uint16_t demobilize_plan(uint8_t part) {
    uint8_t f,s,i;uint16_t allied,enemy,n;
    f=(uint8_t)r(gp_sector+0x3fe);s=world_slot;if(f>=4)return 0;
    n=r(gp_sector+0x2f4+(uint16_t)f*2);if(!n)return 0;
    if(!part) {
        balance(s,f,&allied,&enemy);
        if(allied>=percent((uint16_t)(r(gp_personality+0x24)*75)/100,enemy))return 0;
        return n;
    }
    for(i=0;i<4;++i)if((ng_state[NG_ACTIVE]&(1<<i)) && ng_units[s][i] && !(gp_alliances[f]&(1<<i)))return 0;
    n=(uint16_t)(n*r(gp_personality+0x2e))/100;return n?n:1;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
extern void gp_ensure_strategy(void);
#pragma code-name ("BATTLE")
#else
#define gp_ensure_strategy() ((void)0)
#endif
uint8_t ng_expedition(void) {
    uint8_t s,f,mode,target,origin;uint16_t reachable;
    if(draw(100)>=r(gp_personality+0x18))return 0;
    s=world_slot;f=(uint8_t)r(gp_sector+0x3fe);ng_cache();reachable=ng_route_mask(s,f);mode=2;
    while(mode) {
        --mode;gp_ensure_strategy();ng_expedition_plan(mode,reachable);target=gp_plan[0];if(target==255)continue;
        ng_rule(53,r(gp_plan+2),r(gp_plan+4),gp_plan[6]);if(!r(gp_request+12))continue;
        ng_cache();get(target);origin=ng_state[NG_ORIGIN];ng_state[NG_ORIGIN]=s;
        ng_rule(20,f,0,0);ng_state[NG_ORIGIN]=origin;ng_cache();get(s);ng_event|=16;return 1;
    }
    return 0;
}

#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name ("UIRODATA")
#endif
uint8_t ng_demobilize(uint8_t part) {
    uint8_t f,i,selected[11];uint16_t n,take;
    if(!part) {ng_rule(58,0,0,0);if(r(gp_request+12))return 0;}
    ng_cache();gp_ensure_strategy();n=demobilize_plan(part);if(!n)return 0;
    f=(uint8_t)r(gp_sector+0x3fe);ng_rule(28,f,0,0);
    if(!part) {ng_rule(29,0,0,0);return 1;}
    i=11;while(i) {--i;take=gp_army[i];if(take>n)take=n;selected[i]=(uint8_t)take;gp_army[i]-=(uint8_t)take;n-=take;}
    ng_rule(20,f,0,0);for(i=0;i<11;++i)gp_army[i]=selected[i];ng_rule(29,0,0,0);return 1;
}

#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name ("BATTLE")
#endif
uint8_t ng_roam(void) {
    uint8_t sos,s,f,target,origin;uint16_t reachable;
    s=world_slot;ng_cache();ng_rule(58,0,0,0);sos=(uint8_t)r(gp_request+12);
    gp_ensure_strategy();f=roaming_faction(sos);if(f==255)return 0;
    reachable=gp_plan[10]?65535:ng_route_mask(s,f);
    gp_ensure_strategy();roaming_plan(f,reachable);target=gp_plan[0];if(target==255)return 0;
    ng_rule(28,f,0,0);ng_cache();ng_rule(56,f,0,0);if(r(gp_request+12))ng_rule(54,f,0,0);
    get(target);origin=ng_state[NG_ORIGIN];ng_state[NG_ORIGIN]=s;ng_rule(20,f,0,0);ng_state[NG_ORIGIN]=origin;
    ng_cache();get(s);ng_state[NG_ROAM_COOL]=3;ng_event|=16;return 1;
}
