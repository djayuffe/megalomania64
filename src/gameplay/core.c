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
    }
}
