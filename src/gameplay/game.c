/* C64 campaign policy and orchestration of the independently verified rules.
 * Combat primitives and budgets reproduce DOS; AI choices are native C64 policy. */
#include "game.h"
#ifdef __CC65__
#pragma code-name ("BATTLE")
#endif
static uint8_t retired_owner[16];
uint8_t ng_state[NG_STATE_BYTES],ng_terrain[16],ng_owners[16],ng_ages[16],ng_ruined[16],ng_event,ng_ai_turns;
uint16_t ng_people[16],ng_units[16][4],ng_strength[16][4],ng_presence[4];
static uint16_t rw(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void ww(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static uint16_t r(uint16_t at) {return rw(gp_sector+at);}
static void w(uint16_t at,uint16_t n) {ww(gp_sector+at,n);}
void ng_rule(uint8_t op,uint16_t a,uint16_t b,uint16_t c) {
    uint8_t i;for(i=0;i<32;++i)gp_request[i]=0;
    gp_request[0]=op;ww(gp_request+2,a);ww(gp_request+4,b);ww(gp_request+6,c);
    ww(gp_request+10,rw(ng_state+NG_SEED));
    gp_request[24]=op>=33?ng_state[NG_ISLAND]:ng_state[NG_ORIGIN];
    gp_request[26]=ng_state[NG_HOTSEAT]?(uint8_t)r(0x3fe):ng_state[NG_HUMAN];
    if(op==51)ww(gp_request+14,c);
    if(op==53)ww(gp_request+8,rw(gp_plan+8));
    gp_request[28]=world_last;gp_request[30]=ng_state[NG_ACTIVE];
    gp_dispatch();ww(ng_state+NG_SEED,rw(gp_request+10));
    if((op==33 || op==34 || op==37) && rw(gp_request+18)) {
        i=(uint8_t)r(0x400);ww(ng_state+NG_RESERVE+(uint16_t)i*2,rw(ng_state+NG_RESERVE+(uint16_t)i*2)+rw(gp_request+18));
    }
    if(op==33 && gp_request[20])ng_event|=1;
    if(op==15 && gp_request[20])ng_event|=4;
    if((op==11 || op==31) && gp_request[20])ng_event|=2;
}
void ng_reset_pacts(void) {
    uint8_t i;
    for(i=0;i<4;++i) {gp_alliances[i]=1<<i;ng_state[NG_ALLIES+i]=1<<i;}
    for(i=0;i<32;++i)ng_state[NG_TRUCE+i]=0;
}
static void new_impl(void);
void ng_new(void) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    extern void gp_ensure_rare(void);gp_ensure_rare();
#endif
    new_impl();
}
void ng_cache(void) {
    uint8_t i,s;s=world_slot;world_put();
    ng_ruined[s]=(gp_sector[0x448]&64)!=0;
    ng_owners[s]=ng_ruined[s]?255:(uint8_t)r(0x3fe);
    retired_owner[s]=(gp_sector[0x448]&32)?(uint8_t)r(0x400):255;
    ng_people[s]=r(GP_POP);ng_ages[s]=(uint8_t)r(0x418);
    for(i=0;i<4;++i) {ng_units[s][i]=r(0x2f4+(uint16_t)i*2);ng_strength[s][i]=r(0x3f4+(uint16_t)i*2);}
}
static void get(uint8_t s) {world_slot=s;world_get();}
static void sync_pacts(void) {
    uint8_t i;for(i=0;i<4;++i)ng_state[NG_ALLIES+i]=gp_alliances[i];
}
void ng_break(uint8_t other) {
    uint8_t human;human=ng_state[NG_HUMAN];if(other>=4 || other==human || !(gp_alliances[human]&(1<<other)))return;
    ng_rule(44,human,0,0);sync_pacts();
}
#if defined(__CC65__) && defined(NATIVE_GAME)
extern void gp_ensure_rare(void);
extern void gp_ensure_campaign(void);
extern void gp_ensure_strategy(void);
#pragma code-name (push, "CAMPAIGN")
#endif
static uint16_t route_mask_impl(uint8_t from,uint8_t faction) {
    uint8_t i,s;s=world_slot;ng_cache();
    for(i=0;i<16;++i) {
        if(!ng_terrain[i] || ng_ruined[i])gp_routes[i]=0;
        else {get(i);ng_rule(41,faction,0,0);gp_routes[i]=rw(gp_request+12)?1:3;}
    }
    get(s);ng_rule(42,from,0,0);return rw(gp_request+12);
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "CODE")
#endif
static uint8_t move_impl(uint8_t from,uint8_t to,uint8_t faction) {
    uint8_t success,air,i,ground[11];
    if(from>=16 || to>=16 || from==to || faction>=4 || !ng_terrain[to] || ng_ruined[to])return 0;
    air=!(route_mask_impl(from,faction)&((uint16_t)1<<to));
    get(from);if(!r(0x2f4+(uint16_t)faction*2))return 0;
    if(air && !gp_sector[0x2c8+(uint16_t)faction*11+6] && !gp_sector[0x2c8+(uint16_t)faction*11+7] && !gp_sector[0x2c8+(uint16_t)faction*11+8] && !gp_sector[0x2c8+(uint16_t)faction*11+9])return 0;
    ng_rule(28,faction,0,0);ng_cache();
    for(i=0;i<11;++i) {ground[i]=0;if(air && (i<6 || i>9)) {ground[i]=gp_army[i];gp_army[i]=0;}}
    ng_rule(56,faction,0,0);if(rw(gp_request+12))ng_rule(54,faction,0,0);
    get(to);ng_rule(20,faction,0,0);success=rw(gp_request+12)==0;ng_cache();
    for(i=0;i<11;++i)gp_army[i]+=ground[i];
    get(from);ng_rule(20,faction,0,0);ng_cache();ng_event|=16;return success;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
#pragma code-name (pop)
#endif
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "AUXCODE")
#endif
uint16_t ng_route_mask(uint8_t from,uint8_t faction) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_campaign();
#endif
    return route_mask_impl(from,faction);
}
uint8_t ng_move(uint8_t from,uint8_t to,uint8_t faction) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_campaign();
#endif
    return move_impl(from,to,faction);
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
#endif
static uint8_t pay(uint8_t category,uint8_t age) {
    if(age>=10 || category>=3 || !(r(0x122+(uint16_t)category*2)&(1<<age)))return 0;
    ng_rule(45,1,category,age);return rw(gp_request+12)!=0;
}

uint8_t ng_arm(uint8_t age) {
    uint8_t faction,i;uint16_t crew,n;
    faction=(uint8_t)r(0x3fe);if(faction>=4 || age>=10 || age==8)return 0;
    crew=rw(gp_army_rules+44+(uint16_t)age*2);n=r(GP_FREE);
    if(n<=crew || r(0x2f4+(uint16_t)faction*2)>=250 || !pay(2,age))return 0;
    w(GP_POP,r(GP_POP)-crew);ng_rule(0,n-crew,0,0);
    for(i=0;i<11;++i)gp_army[i]=0;gp_army[age]=1;ng_rule(20,faction,0,0);return 1;
}
static uint8_t defend_impl(uint8_t age,uint8_t building,uint8_t slot);
uint8_t ng_defend(uint8_t age,uint8_t building,uint8_t slot) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_campaign();
#endif
    return defend_impl(age,building,slot);
}
static uint8_t repair_equipment(uint8_t age,uint8_t building);
uint8_t ng_repair(uint8_t age,uint8_t building) {
    return repair_equipment(age,building);
}
uint8_t ng_launch(uint8_t from,uint8_t to,uint8_t faction,uint8_t retaliate) {
    uint8_t i,ok;
    if(from>=16 || to>=16 || faction>=4 || from==to || !ng_terrain[to] || ng_ruined[to])return 0;
    get(to);if(gp_sector[0x444]) {get(from);return 0;}
    get(from);
    if(!retaliate && (r(0x3fe)!=faction || !pay(2,8)))return 0;
    ng_cache();get(to);for(i=0;i<11;++i)gp_army[i]=0;gp_army[8]=1;
    ng_state[NG_ORIGIN]=retaliate?255:from;ng_rule(20,faction,0,0);ok=gp_sector[0x444]!=0;ng_cache();
    get(from);ng_event|=8;return ok;
}
static void remove_turret(uint8_t slot) {
    uint8_t b;if(slot<4)b=0;else if(slot<6) {b=1;slot-=4;}else if(slot==6) {b=2;slot=0;}else {b=3;slot-=7;}
    ng_rule(23,slot,b,0);
}
static void nuclear(uint16_t elapsed) {
    uint8_t old,now,i,s,f,origin;
    old=gp_sector[0x444];if(!old)return;
    now=elapsed>=old?0:old-(uint8_t)elapsed;gp_sector[0x444]=now;
    f=(uint8_t)r(0x3fe);s=world_slot;origin=(uint8_t)r(0x440);
    if(f<4 && old>60 && now<=60 && origin<16)for(i=0;i<10;++i)if(gp_sector[0x3b8+i]==8) {
        remove_turret(i);ng_cache();ng_launch(s,origin,f,1);get(s);break;
    }
    if(f<4 && old>25 && now<=25)for(i=0;i<10;++i)if(gp_sector[0x3b8+i]==9) {
        remove_turret(i);gp_sector[0x444]=0;ng_event|=8;return;
    }
    if(!now) {ng_rule(37,r(0x43e),0,0);gp_sector[0x444]=0;ng_event|=8;}
}
void ng_negotiate(uint8_t other) {
    uint8_t h;h=ng_state[NG_HUMAN];if(other>=4 || other==h || !ng_presence[other])return;
    if(ng_presence[h]<ng_presence[other])return;
    ng_rule(43,h,other,0);sync_pacts();ng_event|=32;
}
void ng_clock(uint16_t elapsed) {ww(ng_state+NG_CLOCK,rw(ng_state+NG_CLOCK)+elapsed);}
static void outcome_impl(void);
void ng_outcome(void) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_rare();
#endif
    outcome_impl();
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "RARE")
#endif
static void outcome_impl(void) {
    uint8_t s,f,h,alive;h=ng_state[NG_HUMAN];alive=0;
    for(f=0;f<4;++f) {ng_presence[f]=0;gp_owned[f]=0;gp_retired[f]=0;gp_army_sectors[f]=0;}
    for(s=0;s<16;++s)if(ng_terrain[s] && !ng_ruined[s]) {
        if(retired_owner[s]<4)++gp_retired[retired_owner[s]];
        f=ng_owners[s];if(f<4) {++gp_owned[f];alive|=1<<f;ng_presence[f]+=ng_people[s]+1;}
        for(f=0;f<4;++f)if(ng_units[s][f]) {++gp_army_sectors[f];alive|=1<<f;ng_presence[f]+=ng_units[s][f];}
    }
    if(ng_state[NG_STATUS]!=NG_PLAYING || ng_state[NG_PHASE])return;
    if(!(alive&(1<<h)) && ng_state[NG_HOTSEAT] && alive) {for(h=0;!(alive&(1<<h));++h) {}ng_state[NG_HUMAN]=h;}
    if(!(alive&(1<<h)))ng_state[NG_STATUS]=(ng_state[NG_WITHDRAW]&(1<<h))?NG_WON:NG_LOST;
    else if(!(alive&~gp_alliances[h]))ng_state[NG_STATUS]=ng_state[NG_ISLAND]==27?NG_COMPLETE:NG_WON;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
#pragma code-name (push, "RARE")
#endif
static void new_impl(void) {
    uint8_t i;for(i=0;i<NG_STATE_BYTES;++i)ng_state[i]=0;ng_ai_turns=0;
    ng_state[NG_ACTIVE]=3;ng_state[NG_SPEED]=1;ng_state[NG_DIFFICULTY]=1;
    ng_state[NG_CATEGORY]=2;ng_state[NG_ORIGIN]=255;ng_state[NG_NUKE]=255;
    ww(ng_state+NG_SEED,0x1991);
    ng_reset_pacts();ww(ng_state+NG_POOL,100);ww(ng_state+NG_DEPLOY,20);ng_state[NG_PHASE]=1;ng_state[NG_PAUSED]=1;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "CAMPAIGN")
#endif
static uint8_t defend_impl(uint8_t age,uint8_t building,uint8_t slot) {
    uint16_t crew,at,n;
    if(age>=10 || building>=4 || !(gp_sector[0x446]&(1<<building)) || slot>=rw(gp_buildings+(uint16_t)building*24+20))return 0;
    at=rw(gp_buildings+(uint16_t)building*24+22)+slot;
    if(gp_sector[at]!=255)return 0;
    crew=rw(gp_defence_rules+40+(uint16_t)age*2);n=r(GP_FREE);
    if(n<crew || !pay(1,age))return 0;
    ng_rule(0,n-crew,0,0);ng_rule(22,slot,building,age);return 1;
}
#ifdef __CC65__
#if defined(NATIVE_GAME)
#pragma code-name (pop)
#endif
#pragma code-name (push, "CODE")
#endif
static uint8_t repair_equipment(uint8_t age,uint8_t building) {
    if(age>=10 || building>=4 || !(gp_sector[0x446]&(1<<building)) || r(0x3d6+(uint16_t)building*2)>=rw(gp_buildings+(uint16_t)building*24+r(0x418)*2) || !pay(0,age))return 0;
    ng_rule(40,0,building,age);return (uint8_t)rw(gp_request+12);
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "CAMPAIGN")
#endif
static void prepare_impl(void) {
    uint8_t i,f,count,start,h,order,k;uint16_t men;
    count=world_factions;h=ng_state[NG_HUMAN];start=ng_state[NG_START];
    if(ng_state[NG_ORDER_EPOCH]!=ng_state[NG_ISLAND]/3+1) {
        for(i=0;i<3;++i) {ng_rule(7,24,0,0);ng_state[NG_ORDER+2-i]=(uint8_t)rw(gp_request+12);}
        ng_state[NG_ORDER_EPOCH]=ng_state[NG_ISLAND]/3+1;
    }
    order=ng_state[NG_ORDER+ng_state[NG_ISLAND]%3]*4;
    ng_state[NG_ACTIVE]=1<<h;
    for(i=0;i<4 && count>1;++i) {f=world_orders[order+i];if(f!=h) {ng_state[NG_ACTIVE]|=1<<f;--count;}}
    if(ng_state[NG_ISLAND]==27) {
        ng_state[NG_ACTIVE]=0;for(i=0;i<4;++i)if(rw(ng_state+NG_RESERVE+(uint16_t)i*2)/10)ng_state[NG_ACTIVE]|=1<<i;
    }
    ng_reset_pacts();ng_state[NG_ROAM_COOL]=0;
    for(i=0;i<16;++i)if(ng_terrain[i]) {get(i);ng_rule(26,0,0,0);ng_cache();}
    if(!ng_state[NG_PHASE] && ng_state[NG_STATUS]==NG_PLAYING) {
        get(start);men=rw(ng_state+NG_DEPLOY);ng_rule(39,h,men?men-1:0,0);ng_cache();
        for(k=0;k<4;++k) {
            f=world_orders[order+k];if(f==h || !(ng_state[NG_ACTIVE]&(1<<f)))continue;
            /* CS0:11E3 rejection sampling, bounded by an available neutral tile. */
            do {ng_rule(7,16,0,0);i=(uint8_t)rw(gp_request+12);}while(!ng_terrain[i] || ng_owners[i]!=4);
            get(i);men=ng_state[NG_ISLAND]==27?rw(ng_state+NG_RESERVE+(uint16_t)f*2)/10:world_enemy_men;
            ng_rule(39,f,men?men-1:0,0);ng_cache();
        }
    }
    if(!ng_state[NG_PHASE] && ng_state[NG_STATUS]!=NG_PLAYING)ng_state[NG_ACTIVE]=0;
    ng_state[NG_SELECTED]=start;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
#endif
static void shutdown_impl(void) {
    uint8_t f;uint16_t n;f=(uint8_t)r(0x3fe);if(f>=4 || !(gp_sector[0x448]&16) || (gp_sector[0x448]&32))return;
    ng_rule(38,0,0,0);n=rw(gp_request+12);
    ww(ng_state+NG_RESERVE+(uint16_t)f*2,rw(ng_state+NG_RESERVE+(uint16_t)f*2)+n);ng_state[NG_WITHDRAW]|=1<<f;ng_event|=2;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
extern void gp_ensure_rare(void);
#endif
void ng_prepare_island(void) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_campaign();
#endif
    prepare_impl();
}
void ng_shutdown(void) {
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_rare();
#endif
    shutdown_impl();
}
static void ai(uint16_t elapsed) {
    uint8_t f,i,s,acted;uint16_t at,timer;
    s=world_slot;if(ng_state[NG_HOTSEAT])return;
    at=NG_AI+(uint16_t)s*2;timer=rw(ng_state+at)+elapsed;
    if(timer<(uint16_t)(4-ng_state[NG_DIFFICULTY])*10) {ww(ng_state+at,timer);return;}ww(ng_state+at,0);
    acted=0;if(ng_state[NG_ROAM_COOL])--ng_state[NG_ROAM_COOL];else acted=ng_roam();
    f=(uint8_t)r(0x3fe);if(f>=4 || f==ng_state[NG_HUMAN] || (gp_sector[0x448]&32))return;
#if defined(__CC65__) && defined(NATIVE_GAME)
    gp_ensure_strategy();
#endif
    ng_personality(f);ng_rule(48,0,0,0);ng_rule(51,0,0,world_first);
    if(!acted) {
        ng_rule(58,0,0,0);
        if(rw(gp_request+12)) {ng_rule(57,0,0,world_first);if(rw(gp_request+12)) {ng_rule(20,f,0,0);acted=1;}}
        if(!acted) {ng_rule(59,0,0,0);acted=(uint8_t)rw(gp_request+12);}
        if(!acted)acted=ng_demobilize(0);
        if(!acted)acted=ng_expedition();
        if(!acted)ng_demobilize(1);
    }
    ng_rule(52,0,0,0);ng_rule(60,0,0,world_first);for(i=0;i<28;++i)gp_plan[i]=0;
    ng_rule(50,0,0,world_first);ng_rule(47,0,0,0);ng_rule(49,0,0,0);++ng_ai_turns;
}
void ng_step(uint16_t elapsed) {
    uint8_t owner;owner=(uint8_t)r(0x3fe);if(gp_sector[0x448]&64) {ng_cache();return;}
    nuclear(elapsed);if(gp_sector[0x448]&64) {ng_cache();return;}
    if(owner<4) {ng_rule(1,elapsed,0,0);ng_rule(3,elapsed,0,0);ng_rule(11,elapsed,0,0);ng_rule(15,elapsed,0,0);ng_rule(14,elapsed,0,0);ng_rule(27,elapsed,0,0);}
    ng_rule(33,elapsed,0,world_first);ng_rule(31,elapsed,0,0);ng_rule(9,0,0,0);ai(elapsed);ng_cache();
}
