/* Native translations of audited DOS gameplay routines. See
 * docs/GAMEPLAY_PORT.md for entry points and what is not yet translated.
 * No original executable bytes or extracted game tables are embedded here. */
#include "core.h"
uint8_t gp_sector[GP_SECTOR_BYTES];
uint8_t gp_request[GP_REQ_BYTES];
uint8_t gp_recipe[10];
uint8_t gp_classes[20];
uint8_t gp_buildings[96];
uint8_t gp_patterns[270];
uint8_t gp_groups[20];
uint8_t gp_complexity[14];
uint8_t gp_manufacture[14];
uint8_t gp_research_points[12];
uint8_t gp_technology_points[20];
uint8_t gp_army[11];
uint8_t gp_army_rules[66];
uint8_t gp_defence_rules[60];
uint8_t gp_alliances[4];
uint8_t gp_combat_rules[10];
uint8_t gp_repair_caps[80];
uint8_t gp_shield_rules[20];
uint8_t gp_owned[4],gp_retired[4],gp_army_sectors[4];

static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}
static void wr16(uint8_t *p, uint16_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
}
static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)rd16(p) | ((uint32_t)rd16(p+2)<<16);
}
static void wr32(uint8_t *p,uint32_t v) {
    wr16(p,(uint16_t)v);wr16(p+2,(uint16_t)(v>>16));
}
static uint16_t worker_rate(uint16_t workers) {
    return workers-(workers>>5);
}
static void set_free(uint16_t men) {
    uint16_t n;
    wr16(gp_sector+GP_FREE,men);
    n=men+1;
    if(n>=500)n=0;
    wr32(gp_sector+GP_BIRTH_DEADLINE,6000UL);
    wr16(gp_sector+GP_BIRTH_RATE,worker_rate(n));
}
/* 11B9:1487: unused tower population reproduces; workers outside the tower
 * do not count toward this rate. The original cap is 998, not the fan cap 90. */
static void birth_tick(uint16_t elapsed) {
    uint32_t deadline,progress;
    uint16_t rate;
    deadline=rd32(gp_sector+GP_BIRTH_DEADLINE);
    rate=rd16(gp_sector+GP_BIRTH_RATE);
    if(deadline==0xffffffffUL || !rate || !deadline)return;
    progress=rd32(gp_sector+GP_BIRTH_PROGRESS)+(uint32_t)elapsed*rate;
    while(progress>=deadline) {
        progress-=deadline;
        if(rd16(gp_sector+GP_POP)!=998) {
            wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)+1);
            set_free(rd16(gp_sector+GP_FREE)+1);
        }
    }
    wr32(gp_sector+GP_BIRTH_PROGRESS,progress);
}
/* 11B9:1378: preserve progress when reallocating a deposit's miners. */
static void assign_miners(uint16_t slot,uint16_t men) {
    uint8_t *d;
    if(slot>=4)return;
    d=gp_sector+GP_DEPOSITS+slot*16;
    if(rd16(d+12)==0xffff || !rd16(d+14))return;
    set_free(rd16(gp_sector+GP_FREE)+rd16(d)-men);
    wr16(d,men);wr32(d+2,3000UL);wr16(d+10,worker_rate(men));
}
/* 11B9:1678: deposits have independent 32-bit progress. Exhaustion returns
 * every assigned miner and disables the task. Gatherables use another path. */
static void mining_tick(uint16_t elapsed) {
    uint8_t slot,*d;
    uint16_t element,rate,left;
    uint32_t deadline,progress;
    for(slot=0;slot<4;++slot) {
        d=gp_sector+GP_DEPOSITS+(uint16_t)slot*16;
        element=rd16(d+12);deadline=rd32(d+2);rate=rd16(d+10);
        if(element>=20 || !gp_classes[element] || deadline==0xffffffffUL || !rate || !deadline)continue;
        progress=rd32(d+6)+(uint32_t)elapsed*rate;
        left=rd16(d+14);
        while(left && progress>=deadline) {
            progress-=deadline;
            wr16(gp_sector+GP_STOCKS+element*2,rd16(gp_sector+GP_STOCKS+element*2)+1);
            --left;
            if(!left) {
                set_free(rd16(gp_sector+GP_FREE)+rd16(d));
                wr16(d,0);progress=0;wr16(d+10,0);wr32(d+2,0xffffffffUL);
                gp_request[20]|=(uint8_t)(1U<<slot);
            }
        }
        wr16(d+14,left);wr32(d+6,progress);
    }
}
/* 0D24:2AF1,2BD5: five (element,cost) pairs; $ff marks an unused pair. */
static uint16_t can_make(void) {
    uint8_t i,element,cost;
    uint16_t count,n;
    count=200;
    for(i=0;i<10;i+=2) {
        element=gp_recipe[i];cost=gp_recipe[i+1];
        if(element==255)continue;
        if(element>=20 || !cost)return 0;
        n=rd16(gp_sector+GP_STOCKS+(uint16_t)element*2)/cost;
        if(n<count)count=n;
    }
    return count;
}
static uint16_t spend(uint16_t count) {
    uint8_t i,element;
    uint16_t required;
    for(i=0;i<10;i+=2) {
        element=gp_recipe[i];
        if(element==255)continue;
        if(element>=20)return 0;
        required=(uint16_t)gp_recipe[i+1]*count;
        if(required>rd16(gp_sector+GP_STOCKS+(uint16_t)element*2))return 0;
    }
    for(i=0;i<10;i+=2) {
        element=gp_recipe[i];
        if(element==255)continue;
        required=(uint16_t)gp_recipe[i+1]*count;
        wr16(gp_sector+GP_STOCKS+(uint16_t)element*2,
             rd16(gp_sector+GP_STOCKS+(uint16_t)element*2)-required);
    }
    return 1;
}
static uint16_t random_bounded(uint16_t bound) {
    uint16_t seed,modulus,value;
    if(!bound)return 0;
    modulus=bound;
    if(!(bound&1))++modulus;
    do {
        seed=rd16(gp_request+10);
        seed=(uint16_t)(seed*2053U+13849U);
        wr16(gp_request+10,seed);
        value=seed%modulus;
        if(value!=bound || (bound&1))break;
        modulus=bound; /* original retry branches past the odd-modulus adjustment */
    }while(1);
    return value;
}
/* 0D24:194B: accessibility is independent of stock already in the tower. */
static void resources_available(void) {
    uint8_t slot,kind,mask,*d;
    uint16_t element;
    for(slot=0;slot<12;++slot)gp_sector[0x432+slot]=0;
    for(slot=0;slot<4;++slot) {
        d=gp_sector+GP_DEPOSITS+(uint16_t)slot*16;
        element=rd16(d+12);
        if(element>=20)continue;
        kind=gp_classes[element];mask=(uint8_t)(1U<<slot);
        if(rd16(d+14) && (!kind || (kind==1 && rd16(gp_sector+0x418)>=1)
                           || (kind==2 && (gp_sector[0x446]&2)))) {
            gp_sector[0x432]|=mask;
            gp_sector[0x433]|=(uint8_t)(1U<<kind);
            wr16(gp_sector+0x436+kind*2,rd16(gp_sector+0x436+kind*2)+1);
            wr16(gp_sector+0x43c,rd16(gp_sector+0x43c)+1);
        }
        if(rd16(gp_sector+GP_STOCKS+element*2)) {
            gp_sector[0x434]|=(uint8_t)(1U<<kind);
            gp_sector[0x435]|=mask;
        }
    }
}
/* 11B9:15D8: reassignment preserves accumulated building progress. */
static void assign_builders(uint16_t kind,uint16_t men) {
    uint8_t *d;
    if(kind<1 || kind>3)return;
    d=gp_sector+0x6c+(kind-1)*24;
    set_free(rd16(gp_sector+GP_FREE)+rd16(d+4)-men);
    wr16(d+4,men);wr32(d+6,24000UL);wr16(d+14,worker_rate(men));
}
/* 0D24:0A04: install the age-specific building and empty its turrets. */
static void complete_building(uint8_t kind) {
    uint8_t *rule;
    uint16_t count,offset,age;
    rule=gp_buildings+(uint16_t)kind*24;
    age=rd16(gp_sector+0x418);
    if(age>=10)return;
    wr16(gp_sector+0x2fc,rd16(gp_sector+0x2fc)+1);
    gp_sector[0x446]|=(uint8_t)(1U<<kind);
    gp_sector[0x447]|=(uint8_t)(1U<<kind);
    wr16(gp_sector+0x3d6+(uint16_t)kind*2,rd16(rule+age*2));
    count=rd16(rule+20);offset=rd16(rule+22);
    while(count && offset<GP_SECTOR_BYTES) {
        gp_sector[offset++]=255;--count;
    }
}
/* 11B9:183E: completion returns builders once and disables the timer. */
static void building_tick(uint16_t elapsed) {
    uint8_t kind,*d;
    uint16_t rate;
    uint32_t deadline,progress;
    for(kind=1;kind<=3;++kind) {
        d=gp_sector+0x6c+(uint16_t)(kind-1)*24;
        deadline=rd32(d+6);rate=rd16(d+14);
        if(deadline==0xffffffffUL || !rate)continue;
        progress=rd32(d+10)+(uint32_t)elapsed*rate;
        wr32(d+10,progress);
        if(progress>=deadline) {
            set_free(rd16(gp_sector+GP_FREE)+rd16(d+4));
            wr16(d+4,0);wr32(d+10,0);wr16(d+14,0);wr32(d+6,0xffffffffUL);
            complete_building(kind);
            gp_request[20]|=(uint8_t)(1U<<kind);
        }
    }
}
/* 1A17:0599: choose each ingredient from its material group. One missing
 * group may be substituted, doubling research complexity. Merely designing
 * a recipe never consumes the real stocks. */
static void design_recipe(uint16_t category,uint16_t age) {
    uint16_t work[20],missing,difference,value;
    uint8_t candidates[20],count,i,j,group,cost,*pattern,index;
    missing=0;
    if(category>=3 || age>=10 || age<rd16(gp_sector+0x418)
       || age-rd16(gp_sector+0x418)>=7)goto failed;
    for(i=0;i<20;++i)work[i]=rd16(gp_sector+GP_STOCKS+(uint16_t)i*2);
    pattern=gp_patterns+(category*10+age)*9;
    for(i=0;i<pattern[0];++i) {
        group=pattern[1+i*2];cost=pattern[2+i*2];count=0;
        if(group>=10 || !cost)goto failed;
        for(j=gp_groups[group*2];j<=gp_groups[group*2+1] && j<20;++j)
            if(work[j]>=cost)candidates[count++]=j;
        if(count)work[candidates[random_bounded(count)]]-=cost;
        else {
            if(missing)goto failed;
            missing=cost;
        }
    }
    if(missing) {
        count=0;
        for(j=0;j<20;++j)if(work[j]>=missing)candidates[count++]=j;
        if(!count)goto failed;
        work[candidates[random_bounded(count)]]-=missing;
    }
    for(i=0;i<10;i+=2)gp_recipe[i]=255;
    index=0;
    for(i=0;i<20;++i) {
        difference=rd16(gp_sector+GP_STOCKS+(uint16_t)i*2)-work[i];
        if(difference) {
            if(index>=10)goto failed;
            gp_recipe[index++]=i;gp_recipe[index++]=(uint8_t)difference;
        }
    }
    value=rd16(gp_complexity+(age-rd16(gp_sector+0x418))*2);
    if(missing)value*=2;
    if(!value)goto failed;
    wr16(gp_request+12,value);wr16(gp_request+18,missing?0:1);
    return;
failed:
    for(i=0;i<10;i+=2) {gp_recipe[i]=0;gp_recipe[i+1]=99;}
    wr16(gp_request+12,0);wr16(gp_request+18,0);
}
/* 1471:0187 and 1A17:15E7. A changed design resets progress; changing only
 * the worker count preserves it. The original manufacturing base is 15. */
static void assign_factory(uint16_t men,uint16_t category,uint16_t age,uint16_t run) {
    uint16_t delta;
    if(category>=3 || age>=10)return;
    if(category!=rd16(gp_sector+0xd2) || age!=rd16(gp_sector+0xd4)) {
        if(!(rd16(gp_sector+0x122+category*2)&(1U<<age)))return;
        wr16(gp_sector+0xe4,0);wr32(gp_sector+0xde,0);
        wr16(gp_sector+0xd2,category);wr16(gp_sector+0xd4,age);
    }
    wr16(gp_sector+0xd6,run);
    set_free(rd16(gp_sector+GP_FREE)+rd16(gp_sector+0xd8)-men);
    wr16(gp_sector+0xd8,men);
    delta=age-rd16(gp_sector+0x418);
    if((rd16(gp_sector+0x122+category*2)&(1U<<age))
       && delta<7 && rd16(gp_manufacture+delta*2)) {
        wr32(gp_sector+0xda,9000UL);wr16(gp_sector+0xe2,worker_rate(men));
    }else {
        wr32(gp_sector+0xda,0xffffffffUL);wr16(gp_sector+0xe2,0);
    }
}
static void stop_factory(void) {
    set_free(rd16(gp_sector+GP_FREE)+rd16(gp_sector+0xd8));
    wr16(gp_sector+0xd8,0);wr16(gp_sector+0xe4,0);
    wr32(gp_sector+0xde,0);wr16(gp_sector+0xe2,0);
    wr32(gp_sector+0xda,0xffffffffUL);wr16(gp_sector+0xd2,0xffff);
}
static uint8_t pay_factory(uint16_t category,uint16_t age) {
    uint8_t i;
    uint8_t *recipe;
    recipe=gp_sector+0x19c+category*100+age*10;
    for(i=0;i<10;++i)gp_recipe[i]=recipe[i];
    return (uint8_t)spend(1);
}
/* CS0:CE20: one initial payment, one payment for each subsequent unit,
 * and the original +1 progress carry after completion. Human factories
 * wait for resources; computer factories stop and release their workers. */
static void factory_tick(uint16_t elapsed) {
    uint16_t category,age,mask,n,run,rate;
    uint32_t deadline,progress,increment;
    category=rd16(gp_sector+0xd2);age=rd16(gp_sector+0xd4);
    if(category>=3 || age>=10)return;
    mask=(uint16_t)(1U<<age);
    if(rd16(gp_sector+0xe4)) {
        if(rd16(gp_sector+0x42a+category*2)&mask)wr16(gp_sector+0xe4,0);
        return;
    }
    deadline=rd32(gp_sector+0xda);rate=rd16(gp_sector+0xe2);
    if(deadline==0xffffffffUL || !rate)return;
    if(!(rd16(gp_sector+0x122+category*2)&mask)) {stop_factory();return;}
    increment=(uint32_t)elapsed*rate;
    if(!increment)return;
    progress=rd32(gp_sector+0xde);
    if(!progress && !pay_factory(category,age))goto no_resources;
    progress+=increment;wr32(gp_sector+0xde,progress);
    while(progress>=deadline) {
        progress=progress-deadline+1;wr32(gp_sector+0xde,progress);
        n=rd16(gp_sector+GP_INVENTORY+category*20+age*2)+1;
        if(n>200)n=200;
        wr16(gp_sector+GP_INVENTORY+category*20+age*2,n);
        run=rd16(gp_sector+0xd6);
        if(run) {
            --run;wr16(gp_sector+0xd6,run);
            if(!run) {stop_factory();return;}
        }
        if(!(rd16(gp_sector+0x42a+category*2)&mask) || !pay_factory(category,age))goto no_resources;
    }
    return;
no_resources:
    if(rd16(gp_sector+0x3fe)!=rd16(gp_request+26)) {stop_factory();return;}
    wr16(gp_sector+0xe4,1);wr32(gp_sector+0xde,0);
    assign_factory(0,category,age,rd16(gp_sector+0xd6));
}
/* 0D24:13D7. The nuclear age advances to the special future state via a
 * flag rather than incrementing the ordinary age. Preserve damaged health
 * with the original two integer divisions (including their rounding). */
static void advance_age(void) {
    uint16_t age,hp,ratio,old_max,new_max;
    uint8_t kind;
    age=rd16(gp_sector+0x418);
    if(age==8) {gp_sector[0x448]|=16;return;}
    if(age>=9)return;
    wr16(gp_sector+0x418,age+1);
    old_max=rd16(gp_buildings+age*2);new_max=rd16(gp_buildings+(age+1)*2);
    if(!old_max)return;
    for(kind=0;kind<4;++kind)if(gp_sector[0x446]&(1U<<kind)) {
        hp=rd16(gp_sector+0x3d6+(uint16_t)kind*2);
        ratio=(uint16_t)(((uint32_t)hp*10000UL)/old_max);
        wr16(gp_sector+0x3d6+(uint16_t)kind*2,(uint16_t)(((uint32_t)ratio*new_max)/10000UL));
    }
}
/* CS0:C950: finish one design, credit points only once per design, release
 * inventors, and advance as many ages as the accumulated points allow. */
static void research_tick(uint16_t elapsed) {
    uint16_t category,age,mask,n,current,points,threshold,delta;
    uint32_t deadline,progress;
    category=rd16(gp_sector+0xbe);age=rd16(gp_sector+0xc0);
    deadline=rd32(gp_sector+0xc6);
    if(category>=3 || age>=10 || deadline==0xffffffffUL || !rd16(gp_sector+0xce))return;
    progress=rd32(gp_sector+0xca)+(uint32_t)elapsed*rd16(gp_sector+0xce);
    wr32(gp_sector+0xca,progress);
    if(progress<deadline)return;
    mask=(uint16_t)(1U<<age);
    n=rd16(gp_sector+0x128+category*2);
    if(rd16(gp_sector+0xd0))n|=mask;else n&=(uint16_t)~mask;
    wr16(gp_sector+0x128+category*2,n);
    wr16(gp_sector+0x122+category*2,rd16(gp_sector+0x122+category*2)|mask);
    n=rd16(gp_sector+0x422+category*2);
    if(n&mask) {
        wr16(gp_sector+0x422+category*2,n&(uint16_t)~mask);
        wr16(gp_sector+0x428,rd16(gp_sector+0x428)-1);
    }
    set_free(rd16(gp_sector+GP_FREE)+rd16(gp_sector+0xc4));
    wr16(gp_sector+0xc4,0);wr32(gp_sector+0xca,0);wr16(gp_sector+0xce,0);
    wr32(gp_sector+0xc6,0xffffffffUL);wr16(gp_sector+0xbe,0xffff);
    current=rd16(gp_sector+0x418);delta=age-current;
    n=rd16(gp_sector+0x12e + category*2);
    if(!(n&mask) && delta<6) {
        wr16(gp_sector+0x41a,rd16(gp_sector+0x41a)+rd16(gp_research_points+delta*2));
        wr16(gp_sector+0x12e + category*2,n|mask);
    }
    while(current<9 && current!=rd16(gp_request+28) && !(gp_sector[0x448]&16)) {
        points=rd16(gp_sector+0x41a);threshold=rd16(gp_technology_points+current*2);
        if(points<threshold || !threshold)break;
        wr16(gp_sector+0x41a,points-threshold);advance_age();
        current=rd16(gp_sector+0x418);
    }
    gp_request[20]=1;
}
/* 1471:0000: install a newly generated recipe only when design succeeds.
 * Reassigning inventors on the same design preserves both recipe and work. */
static void assign_research(uint16_t men,uint16_t category,uint16_t age) {
    uint16_t complexity,offset;
    uint8_t i;
    if(category>=3 || age>=10)return;
    if(category!=rd16(gp_sector+0xbe) || age!=rd16(gp_sector+0xc0)) {
        design_recipe(category,age);complexity=rd16(gp_request+12);
        if(!complexity)return;
        wr16(gp_sector+0xc2,complexity);wr16(gp_sector+0xd0,rd16(gp_request+18));
        wr32(gp_sector+0xca,0);wr16(gp_sector+0xbe,category);wr16(gp_sector+0xc0,age);
        offset=0x19c+category*100+age*10;
        for(i=0;i<10;++i)gp_sector[offset+i]=gp_recipe[i];
    }
    set_free(rd16(gp_sector+GP_FREE)+rd16(gp_sector+0xc4)-men);
    wr16(gp_sector+0xc4,men);
    wr32(gp_sector+0xc6,150UL*(uint16_t)(rd16(gp_sector+0xc2)*10U));
    wr16(gp_sector+0xce,worker_rate(men));
}
#ifdef __CC65__
#pragma code-name (push, "LOWCODE")
#endif
/* 0D24:0F91: weapon units and the people crewing them are different counts. */
static uint16_t army_men(const uint8_t *army) {
    uint16_t men;
    uint8_t age;
    men=army[10];
    for(age=0;age<10;++age)men+=(uint16_t)army[age]*rd16(gp_army_rules+44+(uint16_t)age*2);
    return men;
}
/* 1471:0FCD: remove one unit and its contribution to cached strength. */
static void army_casualty(uint16_t faction,uint16_t age) {
    uint16_t power;
    if(faction>=4 || age>=11)return;
    --gp_sector[0x2c8+faction*11+age];
    wr16(gp_sector+0x2f4+faction*2,rd16(gp_sector+0x2f4+faction*2)-1);
    power=rd16(gp_army_rules+22+age*2);
    wr16(gp_sector+0x3f4+faction*2,rd16(gp_sector+0x3f4+faction*2)-power);
    wr16(gp_sector+0x360+faction*22+age*2,rd16(gp_sector+0x360+faction*22+age*2)-power);
}
/* 11B9:141C: neutral tower building uses the selected army's manpower;
 * these workers are not taken from the idle population of an owned tower. */
static void tower_workers(uint16_t faction,uint16_t men) {
    uint8_t *d;
    if(faction>=4)return;
    d=gp_sector+12+faction*24;
    wr16(d+4,men);wr32(d+6,48000UL);wr16(d+14,worker_rate(men));
}
/* 1471:05DE: exactly one active, non-allied army can construct a tower in
 * neutral territory. Merely moving an army into a sector does not capture it. */
static void choose_tower_builders(void) {
    uint16_t selected,old;
    uint8_t faction;
    if(rd16(gp_sector+0x3fe)!=4 || (gp_sector[0x446]&1))return;
    selected=0xffff;
    for(faction=0;faction<4;++faction) {
        if((gp_request[30]&(1U<<faction)) && rd16(gp_sector+0x2f4+(uint16_t)faction*2)) {
            if(selected!=0xffff) {selected=0xffff;break;}
            selected=faction;
        }
    }
    old=rd16(gp_sector+10);
    if(selected!=0xffff && !(gp_alliances[selected]&(uint8_t)~(1U<<selected))) {
        wr16(gp_sector+10,selected);
        tower_workers(selected,army_men(gp_sector+0x2c8+selected*11));
    }else if(old!=0xffff) {
        tower_workers(old,0);wr16(gp_sector+10,0xffff);
    }
}
/* 1A17:165F: admit high-age units first, then unarmed men; keep rejected
 * units in the caller's array. Health belongs to the leading unit of a type.
 * A nuclear launch schedules its flight instead of entering the army array. */
static void army_arrive(uint16_t faction) {
    uint8_t age,old,accepted;
    uint16_t count,power,left;
    uint8_t *units;
    if(faction>=4 || (gp_sector[0x448]&64))return;
    if(gp_army[8]) {
        if(gp_sector[0x444])return;
        gp_sector[0x444]=(uint8_t)(100+random_bounded(40));
        wr16(gp_sector+0x43e,faction);wr16(gp_sector+0x440,rd16(gp_request+24));
        return;
    }
    units=gp_sector+0x2c8+faction*11;left=0;
    age=9;
    while(1) {
        if(gp_army[age]) {
            old=units[age];count=rd16(gp_sector+0x2f4+faction*2);
            accepted=gp_army[age];left+=accepted;
            if(count+accepted>250)accepted=(uint8_t)(250-count);
            wr16(gp_sector+0x2f4+faction*2,count+accepted);
            units[age]+=accepted;
            if(accepted) {
                left-=accepted;gp_army[age]-=accepted;
                power=(uint16_t)accepted*rd16(gp_army_rules+22+(uint16_t)age*2);
                wr16(gp_sector+0x360+faction*22+(uint16_t)age*2,
                     rd16(gp_sector+0x360+faction*22+(uint16_t)age*2)+power);
                wr16(gp_sector+0x3f4+faction*2,rd16(gp_sector+0x3f4+faction*2)+power);
                if(!old)wr16(gp_sector+0x308+faction*22+(uint16_t)age*2,
                             rd16(gp_army_rules+(uint16_t)age*2));
            }
        }
        if(age==10)break;
        if(age==0)age=10;else --age;
    }
    choose_tower_builders();wr16(gp_request+12,left);
}
/* 0D24:1BCD and 0D24:0E4E: per-turret health, strength and crew loss. */
static void defence_install(uint16_t slot,uint16_t building,uint16_t age) {
    uint16_t location,hp_at,power_at,owner,old_power,power;
    uint8_t empty;
    if(building>=4 || age>=10 || slot>=rd16(gp_buildings+building*24+20))return;
    location=rd16(gp_buildings+building*24+22)+slot;
    empty=gp_sector[location]==255;
    if(empty)wr16(gp_sector+0x2fe,rd16(gp_sector+0x2fe)+1);
    gp_sector[location]=(uint8_t)age;
    wr16(gp_sector+0x300+building*2,rd16(gp_sector+0x300+building*2)+1);
    /* Four, two, one and three turret slots, in building order. */
    hp_at=0x3c2;power_at=0x3de;
    if(building>=1) {hp_at+=8;power_at+=8;}
    if(building>=2) {hp_at+=4;power_at+=4;}
    if(building>=3) {hp_at+=2;power_at+=2;}
    wr16(gp_sector+hp_at+slot*2,rd16(gp_defence_rules+age*2));
    old_power=rd16(gp_sector+power_at+slot*2);
    power=rd16(gp_defence_rules+20+age*2);
    wr16(gp_sector+power_at+slot*2,power);
    owner=rd16(gp_sector+0x3fe);
    if(owner>4)return;
    wr16(gp_sector+0x3f4+owner*2,rd16(gp_sector+0x3f4+owner*2)-(empty?0:old_power)+power);
    wr16(gp_sector+0x3f2,rd16(gp_sector+0x3f2)-(empty?0:old_power)+power);
}
static void defence_casualty(uint16_t slot,uint16_t building) {
    uint16_t location,age,power_at,power,owner,crew;
    if(building>=4 || slot>=rd16(gp_buildings+building*24+20))return;
    location=rd16(gp_buildings+building*24+22)+slot;age=gp_sector[location];
    if(age>=10)return;
    wr16(gp_sector+0x2fe,rd16(gp_sector+0x2fe)-1);
    wr16(gp_sector+0x300+building*2,rd16(gp_sector+0x300+building*2)-1);
    gp_sector[location]=255;
    crew=rd16(gp_defence_rules+40+age*2);
    wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-crew);
    power_at=0x3de;
    if(building>=1)power_at+=8;
    if(building>=2)power_at+=4;
    if(building>=3)power_at+=2;
    power=rd16(gp_sector+power_at+slot*2);owner=rd16(gp_sector+0x3fe);
    if(owner>4)return;
    wr16(gp_sector+0x3f4+owner*2,rd16(gp_sector+0x3f4+owner*2)-power);
    wr16(gp_sector+0x3f2,rd16(gp_sector+0x3f2)-power);
}
/* CS0:5E55: choose an enemy faction, then a present weapon class, uniformly.
 * Neither draw is weighted by unit count. The original retains its initial
 * faction list and retries draws that hit an army depleted during this call. */
static uint16_t damage_armies(uint16_t damage,uint16_t attacker,uint16_t first_age) {
    uint8_t factions[4],ages[11],faction_count,age_count,faction,age;
    uint16_t total,hp,at;
    if(!damage || attacker>=4)return damage;
    faction_count=0;total=0;
    faction=4;
    while(faction) {
        --faction;
        if(faction!=attacker && (gp_request[30]&(1U<<faction))
           && !(gp_alliances[attacker]&(1U<<faction))) {
            hp=rd16(gp_sector+0x2f4+(uint16_t)faction*2);
            if(hp) {total+=hp;factions[faction_count++]=faction;}
        }
    }
    while(damage && total) {
        do {faction=factions[random_bounded(faction_count)];}
        while(!rd16(gp_sector+0x2f4+(uint16_t)faction*2));
        age_count=0;
        if(gp_sector[0x2c8+(uint16_t)faction*11+10])ages[age_count++]=10;
        for(age=(uint8_t)first_age;age<=rd16(gp_request+28) && age<10;++age)
            if(gp_sector[0x2c8+(uint16_t)faction*11+age])ages[age_count++]=age;
        if(!age_count)return damage; /* reject inconsistent caller state */
        age=ages[random_bounded(age_count)];
        at=0x308+(uint16_t)faction*22+(uint16_t)age*2;hp=rd16(gp_sector+at);
        if(damage<hp) {wr16(gp_sector+at,hp-damage);damage=0;}
        else {
            damage-=hp;wr16(gp_sector+at,rd16(gp_army_rules+(uint16_t)age*2));
            army_casualty(faction,age);--total;
        }
    }
    return damage;
}
/* CS0:6154: draw one of all ten turret positions, retrying empty positions.
 * Shutdown sectors and allied owners are immune to this damage pass. */
static uint16_t damage_defences(uint16_t damage,uint16_t attacker) {
    uint16_t owner,hp,slot;
    uint8_t building;
    if(!damage || attacker>=4 || (gp_sector[0x448]&32))return damage;
    owner=rd16(gp_sector+0x3fe);
    /* The original early exit returns the alliance predicate (1), rather
     * than restoring the incoming damage budget. Keep this observed quirk. */
    if(owner<4 && (gp_alliances[owner]&(1U<<attacker)))return 1;
    while(damage && rd16(gp_sector+0x2fe)) {
        do {slot=random_bounded(10);}while(gp_sector[0x3b8+slot]==255);
        hp=rd16(gp_sector+0x3c2+slot*2);
        if(damage<hp) {wr16(gp_sector+0x3c2+slot*2,hp-damage);return 0;}
        damage-=hp;
        building=0;
        if(slot>=4) {slot-=4;building=1;
            if(slot>=2) {slot-=2;building=2;
                if(slot>=1) {slot-=1;building=3;}
            }
        }
        defence_casualty(slot,building);
    }
    return damage;
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
/* 11B9:108C: gatherables keep total stock separately from the deposit's
 * remaining raw material. Spending can reduce that remaining amount directly.
 * A small gathered buffer selects a fast, slow or stopped conversion rate. */
static void reconcile_gatherables(void) {
    uint8_t slot,*d;
    uint16_t element,left,stock,workers;
    int16_t buffer;
    for(slot=0;slot<4;++slot) {
        d=gp_sector+GP_DEPOSITS+(uint16_t)slot*16;element=rd16(d+12);left=rd16(d+14);
        if(element>=20 || gp_classes[element] || !left)continue;
        stock=rd16(gp_sector+GP_STOCKS+element*2);buffer=(int16_t)(stock-left);
        if(buffer<0) {
            wr16(d+14,stock);
            if(!stock) {wr32(d+6,0);wr32(d+2,0xffffffffUL);continue;}
            buffer=0;
        }
        workers=800;
        if(buffer>20)workers=130;
        if(buffer>40)workers=0;
        wr32(d+2,2400UL);wr16(d+10,worker_rate(workers));
    }
}
/* 0D24:2336: conversion depletes the raw deposit, leaving total stock
 * unchanged. Reconciliation then adjusts every gatherable's future rate. */
static void gathering_tick(uint16_t elapsed) {
    uint8_t slot,*d;
    uint16_t element,left,rate;
    uint32_t deadline,progress;
    for(slot=0;slot<4;++slot) {
        d=gp_sector+GP_DEPOSITS+(uint16_t)slot*16;element=rd16(d+12);
        deadline=rd32(d+2);rate=rd16(d+10);
        if(element>=20 || gp_classes[element] || deadline==0xffffffffUL || !rate || !deadline)continue;
        progress=rd32(d+6)+(uint32_t)elapsed*rate;left=rd16(d+14);
        while(progress>=deadline) {
            progress-=deadline;--left;
            if(!left) {
                progress=0;wr16(d+10,0);wr32(d+2,0xffffffffUL);
                gp_request[20]|=(uint8_t)(1U<<slot);break;
            }
        }
        wr16(d+14,left);wr32(d+6,progress);
    }
    reconcile_gatherables();
}
/* 11B9:1E18: remove a whole faction's army into the caller's transfer
 * buffer, including clearing its front-unit health and cached strength. */
static uint16_t extract_army(uint16_t faction) {
    uint8_t age;
    uint16_t power,count,at;
    if(faction>=4)return 0;
    power=0;
    for(age=0;age<11;++age) {
        at=0x2c8+faction*11+age;
        gp_army[age]=gp_sector[at];gp_sector[at]=0;
        at=0x360+faction*22+(uint16_t)age*2;
        power+=rd16(gp_sector+at);wr16(gp_sector+at,0);
        wr16(gp_sector+0x308+faction*22+(uint16_t)age*2,0);
    }
    count=rd16(gp_sector+0x2f4+faction*2);wr16(gp_sector+0x2f4+faction*2,0);
    wr16(gp_sector+0x3f4+faction*2,rd16(gp_sector+0x3f4+faction*2)-power);
    choose_tower_builders();return count;
}
/* 11B9:1F93: demobilize crews into the tower and weapons into inventory.
 * Inventory limits and the population cap are applied independently. */
static void return_army(void) {
    uint8_t age;
    uint16_t n,men;
    for(age=0;age<10;++age) {
        n=rd16(gp_sector+GP_INVENTORY+40+(uint16_t)age*2)+gp_army[age];
        if(n>200)n=200;
        wr16(gp_sector+GP_INVENTORY+40+(uint16_t)age*2,n);
    }
    men=army_men(gp_army);
    n=rd16(gp_sector+GP_POP)+men;
    if(n>998)men=998-rd16(gp_sector+GP_POP);
    wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)+men);
    set_free(rd16(gp_sector+GP_FREE)+men);
}
/* CS0:5A9F: install the owner, demobilize its army, then remove the one
 * person consumed by establishing the tower, if an idle person is available. */
static void claim_tower(uint16_t faction) {
    if(faction>=4)return;
    wr16(gp_sector+0x3fe,faction);
    extract_army(faction);return_army();
    if(rd16(gp_sector+GP_FREE)) {
        set_free(rd16(gp_sector+GP_FREE)-1);
        wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-1);
    }
}
/* CS0:CD19: ownership changes only after the selected army completes its
 * tower. All factions' construction timers are then disabled and cleared. */
static void tower_tick(uint16_t elapsed) {
    uint16_t faction,rate;
    uint32_t deadline,progress;
    uint8_t *d,i;
    faction=rd16(gp_sector+10);
    if(faction>=4)return;
    d=gp_sector+12+faction*24;deadline=rd32(d+6);rate=rd16(d+14);
    if(deadline==0xffffffffUL || !rate)return;
    progress=rd32(d+10)+(uint32_t)elapsed*rate;wr32(d+10,progress);
    if(progress<deadline)return;
    complete_building(0);claim_tower(faction);wr16(gp_sector+10,0xffff);
    for(i=0;i<4;++i) {
        d=gp_sector+12+(uint16_t)i*24;
        wr32(d+10,0);wr16(d+14,0);wr32(d+6,0xffffffffUL);wr16(d+4,0);
    }
    gp_request[20]=1;
}
/* CS0:670B: remove a building's defenders and workers. Destruction kills
 * workers; it does not release them to the idle population. Task rates and
 * old health can remain stale behind their disabled timers, as in DOS. */
static void destroy_building(uint16_t kind) {
    uint16_t slot,offset,element;
    uint8_t *d;
    if(kind>=4)return;
    slot=rd16(gp_buildings+kind*24+20);offset=rd16(gp_buildings+kind*24+22);
    while(slot) {
        --slot;
        if(gp_sector[offset+slot]!=255)defence_casualty(slot,kind);
    }
    if(kind==2 && rd16(gp_sector+0xbe)!=0xffff && rd16(gp_sector+0xc0)>=6) {
        wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-rd16(gp_sector+0xc4));
        wr16(gp_sector+0xc4,0);wr16(gp_sector+0xbe,0xffff);
        wr32(gp_sector+0xca,0);wr32(gp_sector+0xc6,0xffffffffUL);
    }
    if(kind==3 && rd16(gp_sector+0xd2)!=0xffff && rd16(gp_sector+0xd4)>=4) {
        wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-rd16(gp_sector+0xd8));
        wr16(gp_sector+0xd8,0);wr16(gp_sector+0xd2,0xffff);
        wr32(gp_sector+0xde,0);wr32(gp_sector+0xda,0xffffffffUL);wr16(gp_sector+0xe4,0);
    }
    if(kind==1)for(slot=0;slot<4;++slot) {
        d=gp_sector+GP_DEPOSITS+slot*16;element=rd16(d+12);
        if(element<20 && gp_classes[element]==2 && rd32(d+2)!=0xffffffffUL) {
            wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-rd16(d));
            wr16(d,0);wr32(d+6,0);wr32(d+2,0xffffffffUL);
        }
    }
    wr16(gp_sector+0x2fc,rd16(gp_sector+0x2fc)-1);
    gp_sector[0x446]&=(uint8_t)~(1U<<kind);
}
#ifdef __CC65__
#pragma code-name (push, "BATTLE")
#endif
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (push, "RARE")
#endif
/* 1471:033C: remove a turret intact, return its weapon and crew. */
static void recall_defence_impl(uint16_t slot,uint16_t building) {
    uint16_t at,age,n,crew;
    if(building>=4 || slot>=rd16(gp_buildings+building*24+20))return;
    at=rd16(gp_buildings+building*24+22)+slot;age=gp_sector[at];if(age>=10)return;
    defence_casualty(slot,building);at=0xfa+age*2;n=rd16(gp_sector+at)+1;
    wr16(gp_sector+at,n>200?200:n);crew=rd16(gp_defence_rules+40+age*2);
    wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)+crew);set_free(rd16(gp_sector+GP_FREE)+crew);
}
/* CS0:6EC4 normal detonation: kill all armies, remove facilities and mark
 * the land uninhabitable. DOS retains the old owner/population behind this flag. */
static uint8_t automatic_shutdown(void);
static void nuclear_explode_impl(void) {
    uint8_t f,age,k;
    for(f=0;f<4;++f)for(age=0;age<11;++age)
        while(gp_sector[0x2c8+(uint16_t)f*11+age])army_casualty(f,age);
    for(k=1;k<4;++k)if(gp_sector[0x446]&(1<<k))destroy_building(k);
    if((gp_sector[0x448]&32) || automatic_shutdown())return;
    if(gp_sector[0x446]&1)destroy_building(0);
    gp_sector[0x448]=(gp_sector[0x448]&127)|64;gp_sector[0x445]=1;
}
/* 0D24:3D7F: release civilian tasks without losing accumulated progress. */
static void stop_tasks(void) {
    uint8_t k,*d;uint16_t at;
    if(rd16(gp_sector+0xbe)!=65535)assign_research(0,rd16(gp_sector+0xbe),rd16(gp_sector+0xc0));
    if(rd16(gp_sector+0xd2)!=65535)assign_factory(0,rd16(gp_sector+0xd2),rd16(gp_sector+0xd4),rd16(gp_sector+0xd6));
    for(k=0;k<4;++k) {
        d=gp_sector+0x134+(uint16_t)k*16;at=rd16(d+12);
        if(at<20 && gp_classes[at] && rd32(d+2)!=0xffffffffUL)assign_miners(k,0);
    }
    for(k=1;k<4;++k)if(rd32(gp_sector+0x6c+(uint16_t)(k-1)*24+6)!=0xffffffffUL)assign_builders(k,0);
}
/* CS0:6B6C. Preserve the original facility mask quirk (1,2,3 rather
 * than 2,4,8), recall defenders, and return the clamped saved population. */
static uint16_t shutdown_impl(void) {
    uint8_t k,j;uint16_t owner,n;
    owner=rd16(gp_sector+0x3fe);if(owner>=4 || gp_sector[0x448]&32)return 0;
    stop_tasks();
    for(k=0;k<4;++k) {j=(uint8_t)rd16(gp_buildings+(uint16_t)k*24+20);
        while(j) {--j;recall_defence_impl(j,k);}
    }
    for(k=1;k<4;++k)if(gp_sector[0x446]&k)destroy_building(k);
    n=rd16(gp_sector+GP_FREE)+1;
    if(owner!=rd16(gp_request+26) && n<100)n=100;
    if(n>500)n=500;
    gp_sector[0x448]|=32;wr16(gp_sector+0x400,owner);
    wr16(gp_sector+0x3fe,4);wr16(gp_sector+0x418,9);
    return n;
}
/* CS0:668F: only one retired sector per computer faction.
 * The original compares owned-sector count to 1, then indexes field-army
 * counts by that count (not by faction). Preserve this observed quirk. */
static uint8_t automatic_shutdown(void) {
    uint16_t owner,n;owner=rd16(gp_sector+0x3fe);
    if(owner>=4 || owner==rd16(gp_request+26) || rd16(gp_request+24)==27 || !(gp_sector[0x448]&16) || gp_retired[owner] || (gp_owned[owner]<2 && !gp_army_sectors[gp_owned[owner]]))return 0;
    n=shutdown_impl();wr16(gp_request+18,n);return 1;
}
/* 0D24:1669: one shield repairs a selected facility, capped at age health. */
static uint16_t repair_impl(uint16_t building,uint16_t age) {
    uint16_t at,n,maximum;
    if(building>=4 || age>=10)return 0;
    at=0x3d6+building*2;maximum=rd16(gp_repair_caps+building*20+rd16(gp_sector+0x418)*2);
    if(rd16(gp_sector+at)==maximum)return 0;
    n=rd16(gp_sector+at)+rd16(gp_shield_rules+age*2);
    wr16(gp_sector+at,n>maximum?maximum:n);return 1;
}
/* CS0:68F4: cease civilian tasks, evacuate surviving defenders and make the
 * sector neutral. DOS uses 16-bit intermediates in its proportional transfer,
 * including its observed zero-capacity result for armies of <=250 units. */
static void tower_loss_impl(uint16_t attacker) {
    uint8_t k,j,age,mask;
    uint16_t total,counts[4],count,capacity,share,n,at,crew;
    if(attacker>=4)return;
    stop_tasks();
    for(k=0;k<4;++k)for(j=0;j<rd16(gp_buildings+(uint16_t)k*24+20);++j) {
        at=rd16(gp_buildings+(uint16_t)k*24+22)+j;age=gp_sector[at];
        if(age<10) {
            defence_casualty(j,k);
            at=0xfa+(uint16_t)age*2;n=rd16(gp_sector+at)+1;
            wr16(gp_sector+at,n>200?200:n);
            crew=rd16(gp_defence_rules+40+(uint16_t)age*2);
            wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)+crew);
            set_free(rd16(gp_sector+GP_FREE)+crew);
        }
    }
    mask=gp_alliances[attacker];total=0;
    for(k=0;k<4;++k) {
        counts[k]=rd16(gp_sector+0x2f4+(uint16_t)k*2);
        if(mask&(1<<k)) {if(counts[k])total+=counts[k];else mask&=(uint8_t)~(1<<k);}
    }
    k=4;
    while(k) {
        --k;if(!(mask&(1<<k)))continue;
        count=rd16(gp_sector+0x2f4+(uint16_t)k*2);
        capacity=(count>250?250:count)-count;
        share=(uint16_t)(counts[k]*1000U)/total;
        n=(uint16_t)(share*rd16(gp_sector+GP_FREE))/1000;
        total-=counts[k];if(capacity>n)capacity=n;
        for(j=0;j<11;++j)gp_army[j]=0;gp_army[10]=(uint8_t)capacity;
        army_arrive(k);set_free(rd16(gp_sector+GP_FREE)-capacity);
        wr16(gp_sector+GP_POP,rd16(gp_sector+GP_POP)-capacity);
    }
    wr16(gp_sector+0x3fe,4);gp_request[20]|=1;
}
/* CS0:6366: pick a present facility uniformly, carry excess damage through
 * destroyed facilities, and release the tower only when its health reaches 0. */
static uint16_t damage_buildings_impl(uint16_t damage,uint16_t attacker) {
    uint16_t owner,hp,at;
    uint8_t kind;
    if(!damage || attacker>=4 || !(gp_sector[0x446]&1) || (gp_sector[0x448]&32))return damage;
    owner=rd16(gp_sector+0x3fe);
    if(owner<4 && (gp_alliances[owner]&(1<<attacker)))return damage;
    while(damage && rd16(gp_sector+0x2fc)) {
        do {kind=(uint8_t)random_bounded(4);}while(!(gp_sector[0x446]&(1<<kind)));
        at=0x3d6+(uint16_t)kind*2;hp=rd16(gp_sector+at);
        if(damage<hp) {wr16(gp_sector+at,hp-damage);return 0;}
        damage-=hp;if(!kind && automatic_shutdown())break;
        destroy_building(kind);gp_request[20]|=2;
        if(!kind) {tower_loss_impl(attacker);break;}
    }
    return damage;
}
#if defined(__CC65__) && defined(NATIVE_GAME)
#pragma code-name (pop)
extern void gp_ensure_rare(void);
#else
#define gp_ensure_rare() ((void)0)
#endif
static void recall_defence(uint16_t slot,uint16_t building) {gp_ensure_rare();recall_defence_impl(slot,building);}
static void nuclear_explode(void) {gp_ensure_rare();nuclear_explode_impl();}
static uint16_t repair_building(uint16_t b,uint16_t a) {gp_ensure_rare();return repair_impl(b,a);}
static uint16_t shutdown_sector(void) {gp_ensure_rare();return shutdown_impl();}
static void tower_loss(uint16_t faction) {gp_ensure_rare();tower_loss_impl(faction);}
static uint16_t damage_buildings(uint16_t damage,uint16_t attacker) {
    if(!damage || !(gp_sector[0x446]&1))return damage;
    gp_ensure_rare();return damage_buildings_impl(damage,attacker);
}
/* CS0:5B10: simultaneous strength snapshot, descending faction order, then
 * army, turret and building damage budgets. Every arithmetic truncation below
 * matches the original word-sized MUL/ADD/DIV sequence rather than wide math. */
static uint16_t battle_scale(uint16_t power,uint16_t elapsed) {
    uint16_t scale;
    scale=rd16(gp_combat_rules+8);if(!scale)return 0;
    return (uint16_t)((uint16_t)(power*elapsed)+scale-1)/scale;
}
static uint16_t battle_share(uint16_t budget,uint8_t pair) {
    uint16_t first,last,percent;
    first=rd16(gp_combat_rules+pair);last=rd16(gp_combat_rules+pair+2);
    if(last<first)return 0;
    percent=first+random_bounded(last-first+1);
    return (uint16_t)((uint16_t)(budget*percent)+99)/100;
}
static void battle_tick(uint16_t elapsed,uint16_t first_age) {
    uint16_t power[4],unarmed[4],damage,initial,remaining,part,unarmed_left;
    uint8_t faction;
    for(faction=0;faction<4;++faction) {
        power[faction]=rd16(gp_sector+0x3f4+(uint16_t)faction*2);
        unarmed[faction]=rd16(gp_sector+0x374+(uint16_t)faction*22);
    }
    faction=4;
    while(faction) {
        --faction;if(!(gp_request[30]&(1<<faction)) || !power[faction] || power[faction]>=32768)continue;
        damage=battle_scale(power[faction],elapsed);if(!damage)continue;
        initial=damage;unarmed_left=battle_scale(unarmed[faction],elapsed);
        if(rd16(gp_sector+0x3fe)==faction) {damage_armies(damage,faction,first_age);continue;}
        part=battle_share(damage,0);remaining=damage_armies(part,faction,first_age);
        damage=damage-part+remaining;
        part=battle_share(damage,4);remaining=damage_defences(part,faction);
        damage=damage-part+remaining;
        if(rd16(gp_request+24)!=27) {
            unarmed_left-=(uint16_t)((uint16_t)((initial-damage)*unarmed_left)/initial);
            damage-=unarmed_left;
        }
        damage_buildings(damage,faction);
    }
    choose_tower_builders();
}
#ifdef __CC65__
#pragma code-name (pop)
#endif
void gp_dispatch(void) {
    uint16_t a,b,c,n;
    a=rd16(gp_request+2);b=rd16(gp_request+4);c=rd16(gp_request+6);
    wr16(gp_request+12,0);gp_request[20]=0;
    switch(gp_request[0]) {
    case 0:set_free(a);break;
    case 1:birth_tick(a);break;
    case 2:assign_miners(b,a);break;
    case 3:mining_tick(a);break;
    case 4:wr16(gp_request+12,can_make());break;
    case 5:wr16(gp_request+12,spend(a));break;
    case 6:
        if(b<3 && c<10) {
            n=rd16(gp_sector+GP_INVENTORY+b*20+c*2)+a;
            if(n>200)n=200;
            wr16(gp_sector+GP_INVENTORY+b*20+c*2,n);
        }
        break;
    case 7:wr16(gp_request+12,random_bounded(a));break;
    case 8:
        wr16(gp_request+12,worker_rate(a));
        wr32(gp_request+22,(uint32_t)(uint16_t)(rd16(gp_request+14)*6U)*rd16(gp_request+16));
        break;
    case 9:resources_available();break;
    case 10:assign_builders(b,a);break;
    case 11:building_tick(a);break;
    case 12:design_recipe(b,c);break;
    case 13:assign_factory(a,b,c,rd16(gp_request+8));break;
    case 14:factory_tick(a);break;
    case 15:research_tick(a);break;
    case 16:advance_age();break;
    case 17:assign_research(a,b,c);break;
    case 18:wr16(gp_request+12,army_men(gp_army));break;
    case 19:army_casualty(b,c);break;
    case 20:army_arrive(a);break;
    case 21:choose_tower_builders();break;
    case 22:defence_install(a,b,c);break;
    case 23:defence_casualty(a,b);break;
    case 24:wr16(gp_request+12,damage_armies(a,b,c));break;
    case 25:wr16(gp_request+12,damage_defences(a,b));break;
    case 26:reconcile_gatherables();break;
    case 27:gathering_tick(a);break;
    case 28:wr16(gp_request+12,extract_army(a));break;
    case 29:return_army();break;
    case 30:claim_tower(a);break;
    case 31:tower_tick(a);break;
    case 32:destroy_building(b);break;
    case 33:battle_tick(a,c);break;
    case 34:wr16(gp_request+12,damage_buildings(a,b));break;
    case 35:tower_loss(a);break;
    case 36:recall_defence(a,b);break;
    case 37:nuclear_explode();break;
    case 38:wr16(gp_request+12,shutdown_sector());break;
    case 40:wr16(gp_request+12,repair_building(b,c));break;
    case 39:wr16(gp_sector+0x3fe,a);complete_building(0);wr16(gp_sector+GP_POP,b);set_free(b);break;
    }
}
