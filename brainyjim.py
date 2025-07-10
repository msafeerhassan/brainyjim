import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime
import os
import aiohttp
import requests
from typing import Optional

# some random variables i might need later
max_facts_per_day = 50
current_trivia_count=0
bot_version="1.0"
last_api_call_time=None
debug_mode=False
fact_limit=1000

facts=[
    "Bananas are berries but strawberries aren't",
    "Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs",
    "A group of flamingos is called a 'flamboyance'",
    "Octopuses have three hearts and blue blood",
    "The shortest war in history lasted only 38-45 minutes",
    "Wombat poop is cube-shaped",
    "There are more possible games of chess than atoms in the observable universe",
    "Sea otters hold hands while sleeping so they don't drift apart",
    "A shrimp's heart is in its head",
    "Butterflies taste with their feet",
    "The Great Wall of China isn't visible from space with the naked eye",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid",
    "Oxford University is older than the Aztec Empire",
    "A day on Venus is longer than its year",
    "Sharks are older than trees",
    "The unicorn is Scotland's national animal",
    "Lobsters were once considered prison food",
    "Bubble wrap was originally invented as wallpaper",
    "The dot over a lowercase 'i' or 'j' is called a tittle",
    "Penguins have knees",
    "A group of pandas is called an embarrassment",
    "Carrots were originally purple",
    "The human brain uses about 20% of the body's total energy",
    "Sloths can rotate their heads 270 degrees",
    "A blue whale's heart is as big as a small car",
    "Dolphins have names for each other",
    "Cats can't taste sweetness",
    "A group of owls is called a parliament",
    "The longest recorded flight of a chicken is 13 seconds",
    "Elephants are afraid of bees",
    "Goldfish have better color vision than humans",
    "A single cloud can weigh more than a million pounds",
    "The human nose can detect about 1 trillion different scents",
    "Koalas sleep 18-22 hours per day",
    "A group of frogs is called an army",
    "Snails can sleep for up to 3 years",
    "The tongue is the strongest muscle in the human body relative to its size",
    "Polar bears have black skin under their white fur",
    "A group of jellyfish is called a smack",
    "Hummingbirds are the only birds that can fly backwards"
]

fact_reactions={}
user_scores={}
daily_trivia={}
user_submitted_facts=[]
api_facts_cache=[]
fact_categories={
    "animals":["Bananas are berries but strawberries aren't","Octopuses have three hearts and blue blood","Sea otters hold hands while sleeping so they don't drift apart","A shrimp's heart is in its head","Butterflies taste with their feet","Penguins have knees","Cats can't taste sweetness","Elephants are afraid of bees","Goldfish have better color vision than humans","Koalas sleep 18-22 hours per day","Snails can sleep for up to 3 years","Polar bears have black skin under their white fur","Hummingbirds are the only birds that can fly backwards"],
    "history":["Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid","Oxford University is older than the Aztec Empire","The shortest war in history lasted only 38-45 minutes","Lobsters were once considered prison food"],
    "science":["There are more possible games of chess than atoms in the observable universe","The Great Wall of China isn't visible from space with the naked eye","A day on Venus is longer than its year","Sharks are older than trees","The human brain uses about 20% of the body's total energy","A single cloud can weigh more than a million pounds","The human nose can detect about 1 trillion different scents"],
    "random":["A group of flamingos is called a 'flamboyance'","Wombat poop is cube-shaped","The unicorn is Scotland's national animal","Bubble wrap was originally invented as wallpaper","The dot over a lowercase 'i' or 'j' is called a tittle","A group of pandas is called an embarrassment","Carrots were originally purple","Sloths can rotate their heads 270 degrees","Dolphins have names for each other","A group of owls is called a parliament","The longest recorded flight of a chicken is 13 seconds","A blue whale's heart is as big as a small car","A group of frogs is called an army","The tongue is the strongest muscle in the human body relative to its size","A group of jellyfish is called a smack"],
    "user_submitted":[]
}

intents=discord.Intents.default()
intents.reactions=True
intents.message_content=True

bot=commands.Bot(command_prefix='!',intents=intents)

CHANNEL_ID=None
daily_channel=None
bot_start_time=datetime.now()

@bot.event
async def on_ready():
    global daily_channel
    try:
        print(f'{bot.user} has connected to Discord!')
        
        synced=await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as error:
        print(f'Failed to sync commands: {error}')
        try:
            await asyncio.sleep(3)
            synced=await bot.tree.sync()
            print(f'Retry sync successful: {len(synced)} command(s)')
        except:
            print("Sync retry failed, continuing anyway...")
    
    if not os.path.exists('fact_data.json'):
        try:
            with open('fact_data.json','w') as f:
                json.dump({},f)
        except Exception as e:
            print(f"Could not create fact_data.json: {e}")
    
    load_fact_data()
    
    initial_facts=len(get_all_facts())
    print(f"Loaded {initial_facts} facts from database")
    
    if len(api_facts_cache)<10:
        print("Loading additional facts from APIs...")
        try:
            await load_more_facts()
            print(f"Now have {len(get_all_facts())} total facts")
        except Exception as e:
            print(f"Error loading facts from APIs: {e}")
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name=='general' or 'general' in channel.name.lower():
                daily_channel=channel
                break
        if daily_channel:
            break
    
    if not daily_channel and bot.guilds:
        try:
            daily_channel=bot.guilds[0].text_channels[0]
        except:
            pass
    
    asyncio.create_task(start_scheduler())

def load_fact_data():
    global fact_reactions,user_scores,daily_trivia,user_submitted_facts,api_facts_cache
    try:
        with open('fact_data.json','r',encoding='utf-8') as f:
            data=json.load(f)
            fact_reactions=data.get('fact_reactions',{})
            user_scores=data.get('user_scores',{})
            daily_trivia=data.get('daily_trivia',{})
            user_submitted_facts=data.get('user_submitted_facts',[])
            api_facts_cache=data.get('api_facts_cache',[])
    except FileNotFoundError:
        print("No existing fact data found, starting fresh...")
        fact_reactions={}
        user_scores={}
        daily_trivia={}
        user_submitted_facts=[]
        api_facts_cache=[]
    except json.JSONDecodeError as e:
        print(f"Error reading fact data JSON: {e}")
        fact_reactions={}
        user_scores={}
        daily_trivia={}
        user_submitted_facts=[]
        api_facts_cache=[]
    except Exception as error:
        print(f"Unexpected error loading fact data: {error}")
        fact_reactions={}
        user_scores={}
        daily_trivia={}
        user_submitted_facts=[]
        api_facts_cache=[]
    
    fact_categories["user_submitted"]=user_submitted_facts
    
    all_facts=[]
    for category_facts in fact_categories.values():
        all_facts.extend(category_facts)
    all_facts.extend(api_facts_cache)
    
    for fact in all_facts:
        if fact not in fact_reactions:
            fact_reactions[fact]={'thumbs_up':0,'thumbs_down':0}

def save_fact_data():
    max_retries=3
    for attempt in range(max_retries):
        try:
            backup_data={
                'fact_reactions':fact_reactions,
                'user_scores':user_scores,
                'daily_trivia':daily_trivia,
                'user_submitted_facts':user_submitted_facts,
                'api_facts_cache':api_facts_cache
            }
            with open('fact_data.json','w',encoding='utf-8') as f:
                json.dump(backup_data,f,indent=2)
            return True
        except Exception as error:
            print(f'Error saving fact data (attempt {attempt+1}): {error}')
            if attempt<max_retries-1:
                asyncio.sleep(0.5)
            else:
                print("Failed to save data after all retries!")
                return False

async def fetch_random_fact_from_api():
    apis=[
        "https://uselessfacts.jsph.pl/random.json?language=en",
        "https://catfact.ninja/fact",
        "https://dog-api.kinduff.com/api/facts",
        "https://meowfacts.herokuapp.com/"
    ]
    
    for api_url in apis:
        try:
            timeout=aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as response:
                    if response.status==200:
                        try:
                            data=await response.json()
                        except:
                            continue
                        
                        fact=None
                        if 'text' in data:
                            fact=data['text']
                        elif 'fact' in data:
                            fact=data['fact']
                        elif 'data' in data and isinstance(data['data'],list) and data['data']:
                            fact=data['data'][0]
                        
                        if fact and len(fact)>10 and len(fact)<500:
                            if fact not in api_facts_cache and fact not in str(get_all_facts()):
                                api_facts_cache.append(fact)
                                fact_reactions[fact]={'thumbs_up':0,'thumbs_down':0}
                                save_fact_data()
                            return fact
        except asyncio.TimeoutError:
            print(f"Timeout fetching from {api_url}")
            continue
        except aiohttp.ClientError as e:
            print(f"Client error fetching from {api_url}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error fetching from {api_url}: {e}")
            continue
    
    return None

def get_all_facts():
    all_facts=[]
    for category_facts in fact_categories.values():
        all_facts.extend(category_facts)
    all_facts.extend(api_facts_cache)
    return list(set(all_facts))

async def load_more_facts():
    print("Loading more facts from APIs...")
    successful_loads=0
    failed_loads=0
    for i in range(8):
        try:
            fact=await fetch_random_fact_from_api()
            if fact:
                print(f"Added new fact: {fact[:50]}...")
                successful_loads+=1
            else:
                failed_loads+=1
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"Error loading fact {i+1}: {e}")
            failed_loads+=1
            continue
    print(f"Successfully loaded {successful_loads} new facts, failed: {failed_loads}")

@bot.tree.command(name='fact',description='Get a random fun fact!')
async def fact_command(interaction:discord.Interaction):
    try:
        all_facts=get_all_facts()
        
        if len(all_facts)<20:
            try:
                await load_more_facts()
                all_facts=get_all_facts()
            except:
                pass
        
        if not all_facts:
            await interaction.response.send_message("Sorry, no facts available right now! Try again later.",ephemeral=True)
            return
            
        fact=random.choice(all_facts)
        
        embed=discord.Embed(
            title="🧠 Fun Fact from BrainyJim!",
            description=fact,
            color=0x3498db
        )
        
        thumbs_up=fact_reactions.get(fact,{}).get('thumbs_up',0)
        thumbs_down=fact_reactions.get(fact,{}).get('thumbs_down',0)
        
        embed.add_field(name="Reactions",value=f"👍 {thumbs_up} | 👎 {thumbs_down}",inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            message=await interaction.original_response()
            await message.add_reaction('👍')
            await message.add_reaction('👎')
        except discord.HTTPException:
            pass
        except Exception as e:
            print(f"Error adding reactions: {e}")
    except Exception as error:
        try:
            await interaction.response.send_message("Something went wrong getting a fact! Please try again.",ephemeral=True)
        except:
            pass
        print(f"Error in fact command: {error}")

@bot.tree.command(name='categoryfact',description='Get a fact from a specific category!')
async def category_fact_command(interaction:discord.Interaction,category:str):
    try:
        if category.lower() not in fact_categories:
            available_cats=', '.join(fact_categories.keys())
            await interaction.response.send_message(f"Invalid category! Choose from: {available_cats}",ephemeral=True)
            return
        
        category_facts=fact_categories[category.lower()]
        if not category_facts:
            await interaction.response.send_message(f"No facts available for {category} category yet!",ephemeral=True)
            return
            
        fact=random.choice(category_facts)
        
        embed=discord.Embed(
            title=f"🧠 {category.title()} Fact from BrainyJim!",
            description=fact,
            color=0x9b59b6
        )
        
        thumbs_up=fact_reactions.get(fact,{}).get('thumbs_up',0)
        thumbs_down=fact_reactions.get(fact,{}).get('thumbs_down',0)
        
        embed.add_field(name="Reactions",value=f"👍 {thumbs_up} | 👎 {thumbs_down}",inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            message=await interaction.original_response()
            await message.add_reaction('👍')
            await message.add_reaction('👎')
        except:
            pass
    except Exception as error:
        try:
            await interaction.response.send_message("Error getting category fact! Try again.",ephemeral=True)
        except:
            pass
        print(f"Error in category fact command: {error}")

@bot.tree.command(name='trivia',description='Play a trivia game!')
async def trivia_command(interaction:discord.Interaction):
    trivia_questions=[
        {"question":"What animal's poop is cube-shaped?","answer":"wombat","options":["koala","wombat","kangaroo","platypus"]},
        {"question":"How many hearts does an octopus have?","answer":"3","options":["2","3","4","5"]},
        {"question":"What is Scotland's national animal?","answer":"unicorn","options":["dragon","unicorn","lion","eagle"]},
        {"question":"How long can a snail sleep?","answer":"3 years","options":["1 year","2 years","3 years","6 months"]},
        {"question":"What was bubble wrap originally invented as?","answer":"wallpaper","options":["packaging","wallpaper","insulation","carpet"]},
        {"question":"What is the dot over a lowercase 'i' called?","answer":"tittle","options":["dot","tittle","point","mark"]},
        {"question":"Which is older: Oxford University or the Aztec Empire?","answer":"oxford","options":["oxford","aztec","same age","unknown"]},
        {"question":"Can cats taste sweetness?","answer":"no","options":["yes","no","only some","depends on breed"]},
        {"question":"Are bananas berries?","answer":"yes","options":["yes","no","sometimes","depends on type"]},
        {"question":"How long was the shortest war in history?","answer":"38-45 minutes","options":["10 minutes","38-45 minutes","2 hours","1 day"]},
        {"question":"What color were carrots originally?","answer":"purple","options":["orange","purple","yellow","white"]},
        {"question":"How many degrees can sloths rotate their heads?","answer":"270","options":["180","270","360","90"]}
    ]
    
    try:
        question_data=random.choice(trivia_questions)
        user_id=str(interaction.user.id)
        
        if user_id not in user_scores:
            user_scores[user_id]={"correct":0,"total":0}
        
        embed=discord.Embed(
            title="🎯 BrainyJim Trivia Challenge!",
            description=f"**Question:** {question_data['question']}\n\n**Options:**\n"+
                       "\n".join([f"{i+1}. {opt}" for i,opt in enumerate(question_data['options'])]),
            color=0xe74c3c
        )
        
        user_score=user_scores[user_id]
        embed.add_field(name="Your Score",value=f"✅ {user_score['correct']}/{user_score['total']} correct",inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            message=await interaction.original_response()
            for i in range(len(question_data['options'])):
                await message.add_reaction(f"{i+1}️⃣")
                await asyncio.sleep(0.2)
        except Exception as e:
            print(f"Error adding trivia reactions: {e}")
        
        daily_trivia[str(message.id)]={
            "answer":question_data['answer'],
            "options":question_data['options'],
            "user_id":user_id
        }
        save_fact_data()
        
    except Exception as error:
        try:
            await interaction.response.send_message("Error starting trivia! Please try again.",ephemeral=True)
        except:
            pass
        print(f"Error in trivia command: {error}")

@bot.tree.command(name='leaderboard', description='See the trivia leaderboard!')
async def leaderboard_command(interaction:discord.Interaction):
    try:
        if not user_scores:
            await interaction.response.send_message("No scores yet! Play some trivia with `/trivia`!",ephemeral=True)
            return
        
        sorted_users=sorted(user_scores.items(),key=lambda x:x[1]['correct'],reverse=True)[:10]
        
        embed=discord.Embed(
            title="🏆 BrainyJim Trivia Leaderboard",
            color=0xf39c12
        )
        
        leaderboard_text=""
        for i,(user_id,score) in enumerate(sorted_users,1):
            try:
                user=await bot.fetch_user(int(user_id))
                username=user.display_name
            except:
                username=f"User {user_id}"
            
            percentage=(score['correct']/score['total']*100) if score['total']>0 else 0
            leaderboard_text+=f"{i}. {username} - {score['correct']}/{score['total']} ({percentage:.1f}%)\n"
        
        embed.description=leaderboard_text
        await interaction.response.send_message(embed=embed)
    except Exception as error:
        try:
            await interaction.response.send_message("Error loading leaderboard! Try again.",ephemeral=True)
        except:
            pass
        print(f"Error in leaderboard command: {error}")

@bot.tree.command(name='mystats', description='Check your personal stats!')
async def mystats_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id not in user_scores:
        await interaction.response.send_message("You haven't played any trivia yet! Try `/trivia` to start!")
        return
    
    score = user_scores[user_id]
    percentage = (score['correct'] / score['total'] * 100) if score['total'] > 0 else 0
    
    embed = discord.Embed(
        title=f"📊 {interaction.user.display_name}'s Stats",
        color=0x3498db
    )
    
    embed.add_field(name="Trivia Score", value=f"✅ {score['correct']}/{score['total']} correct ({percentage:.1f}%)", inline=False)
    
    all_users = list(user_scores.keys())
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1]['correct'], reverse=True)
    
    rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), len(all_users))
    
    embed.add_field(name="Rank", value=f"#{rank} out of {len(all_users)} players", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='categories', description='See all available fact categories!')
async def categories_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Available Fact Categories",
        color=0x9b59b6
    )
    
    for category, facts in fact_categories.items():
        embed.add_field(name=f"{category.title().replace('_', ' ')}", value=f"{len(facts)} facts", inline=True)
    
    embed.add_field(name="API Facts", value=f"{len(api_facts_cache)} facts from APIs", inline=True)
    
    total_facts = len(get_all_facts())
    embed.add_field(name="Total Facts", value=f"{total_facts} facts available!", inline=True)
    
    embed.add_field(name="How to use:", value="Use `/categoryfact [category]` to get a fact from a specific category!", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='submitfact', description='Submit your own fun fact to the database!')
async def submit_fact_command(interaction: discord.Interaction, fact: str):
    if len(fact) < 10:
        await interaction.response.send_message("Your fact is too short! Please make it at least 10 characters long.")
        return
    
    if len(fact) > 500:
        await interaction.response.send_message("Your fact is too long! Please keep it under 500 characters.")
        return
    
    if fact in get_all_facts():
        await interaction.response.send_message("This fact already exists in our database!")
        return
    
    user_submitted_facts.append(fact)
    fact_categories["user_submitted"] = user_submitted_facts
    fact_reactions[fact] = {'thumbs_up': 0, 'thumbs_down': 0}
    save_fact_data()
    
    embed = discord.Embed(
        title="✅ Fact Submitted Successfully!",
        description=f"Thank you for contributing to our fact database!\n\n**Your fact:** {fact}",
        color=0x00ff00
    )
    
    embed.add_field(name="What's next?", value="Your fact is now part of our database and can appear in random fact selections!", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='morefacts', description='Load more facts from online sources!')
async def load_more_facts_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    initial_count = len(get_all_facts())
    await load_more_facts()
    new_count = len(get_all_facts())
    
    facts_added = new_count - initial_count
    
    embed = discord.Embed(
        title="📚 Fact Database Updated!",
        description=f"Successfully added {facts_added} new facts from online sources!",
        color=0x3498db
    )
    
    embed.add_field(name="Total Facts", value=f"{new_count} facts now available", inline=True)
    embed.add_field(name="API Facts", value=f"{len(api_facts_cache)} facts from APIs", inline=True)
    
    await interaction.followup.send(embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    if reaction.emoji in ['👍', '👎']:
        if reaction.message.embeds:
            embed = reaction.message.embeds[0]
            if embed.title and "Fun Fact from BrainyJim!" in embed.title:
                fact_text = embed.description
                
                if fact_text in fact_reactions:
                    if reaction.emoji == '👍':
                        fact_reactions[fact_text]['thumbs_up'] += 1
                    elif reaction.emoji == '👎':
                        fact_reactions[fact_text]['thumbs_down'] += 1
                    
                    save_fact_data()
                    
                    thumbs_up = fact_reactions[fact_text]['thumbs_up']
                    thumbs_down = fact_reactions[fact_text]['thumbs_down']
                    
                    embed.set_field_at(0, name="Reactions", value=f"👍 {thumbs_up} | 👎 {thumbs_down}", inline=False)
                    
                    try:
                        await reaction.message.edit(embed=embed)
                    except:
                        pass
    
    elif reaction.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣']:
        message_id = str(reaction.message.id)
        if message_id in daily_trivia:
            trivia_data = daily_trivia[message_id]
            if str(user.id) == trivia_data['user_id']:
                
                choice_index = int(reaction.emoji[0]) - 1
                selected_answer = trivia_data['options'][choice_index]
                correct_answer = trivia_data['answer']
                
                user_scores[trivia_data['user_id']]['total'] += 1
                
                if selected_answer.lower() == correct_answer.lower():
                    user_scores[trivia_data['user_id']]['correct'] += 1
                    result_emoji = "✅"
                    result_text = "Correct!"
                else:
                    result_emoji = "❌"
                    result_text = f"Wrong! The correct answer was: {correct_answer}"
                
                embed = discord.Embed(
                    title=f"{result_emoji} Trivia Result",
                    description=result_text,
                    color=0x00ff00 if result_emoji == "✅" else 0xff0000
                )
                
                user_score = user_scores[trivia_data['user_id']]
                percentage = (user_score['correct'] / user_score['total'] * 100) if user_score['total'] > 0 else 0
                
                embed.add_field(name="Your Score", value=f"✅ {user_score['correct']}/{user_score['total']} correct ({percentage:.1f}%)", inline=False)
                
                try:
                    await reaction.message.edit(embed=embed)
                    await reaction.message.clear_reactions()
                except:
                    pass
                
                del daily_trivia[message_id]
                save_fact_data()

@bot.event
async def on_reaction_remove(reaction,user):
    if user.bot:
        return
    
    try:
        if reaction.emoji in ['👍','👎']:
            if reaction.message.embeds:
                embed=reaction.message.embeds[0]
                if embed.title and "Fun Fact from BrainyJim!" in embed.title:
                    fact_text=embed.description
                    
                    if fact_text in fact_reactions:
                        if reaction.emoji=='👍' and fact_reactions[fact_text]['thumbs_up']>0:
                            fact_reactions[fact_text]['thumbs_up']-=1
                        elif reaction.emoji=='👎' and fact_reactions[fact_text]['thumbs_down']>0:
                            fact_reactions[fact_text]['thumbs_down']-=1
                        
                        save_fact_data()
                        
                        thumbs_up=fact_reactions[fact_text]['thumbs_up']
                        thumbs_down=fact_reactions[fact_text]['thumbs_down']
                        
                        embed.set_field_at(0,name="Reactions",value=f"👍 {thumbs_up} | 👎 {thumbs_down}",inline=False)
                        
                        try:
                            await reaction.message.edit(embed=embed)
                        except discord.HTTPException:
                            pass
                        except Exception:
                            pass
    except Exception as e:
        print(f"Error in reaction remove handler: {e}")

async def send_daily_fact():
    global daily_channel
    try:
        if daily_channel:
            all_facts=get_all_facts()
            if not all_facts:
                try:
                    await load_more_facts()
                    all_facts=get_all_facts()
                except:
                    print("Failed to load facts for daily fact")
                    return
            
            if not all_facts:
                print("No facts available for daily fact")
                return
                
            fact=random.choice(all_facts)
            
            embed=discord.Embed(
                title="🌅 Daily Fun Fact from BrainyJim!",
                description=fact,
                color=0xe74c3c
            )
            
            thumbs_up=fact_reactions.get(fact,{}).get('thumbs_up',0)
            thumbs_down=fact_reactions.get(fact,{}).get('thumbs_down',0)
            
            embed.add_field(name="Reactions",value=f"👍 {thumbs_up} | 👎 {thumbs_down}",inline=False)
            embed.set_footer(text=f"Daily fact for {datetime.now().strftime('%B %d, %Y')} • {len(all_facts)} facts in database")
            
            message=await daily_channel.send(embed=embed)
            try:
                await message.add_reaction('👍')
                await message.add_reaction('👎')
            except:
                pass
            
            print(f"Sent daily fact: {fact}")
        else:
            print("No daily channel found for daily fact")
    except Exception as error:
        print(f"Error sending daily fact: {error}")

@bot.tree.command(name='guess', description='Guess a number and get a fun fact!')
async def guess_command(interaction: discord.Interaction, number: int):
    if number < 1 or number > 100:
        await interaction.response.send_message("Please guess a number between 1 and 100!")
        return
    
    secret_number = random.randint(1, 100)
    difference = abs(number - secret_number)
    
    all_facts = get_all_facts()
    
    if difference == 0:
        color = 0x00ff00
        title = "🎯 PERFECT GUESS!"
        description = f"Amazing! You guessed exactly {secret_number}!"
    elif difference <= 5:
        color = 0xffff00
        title = "🔥 So Close!"
        description = f"Very close! You guessed {number}, I was thinking of {secret_number}!"
    elif difference <= 15:
        color = 0xff9900
        title = "👍 Good Guess!"
        description = f"Not bad! You guessed {number}, I was thinking of {secret_number}!"
    else:
        color = 0xff0000
        title = "😅 Nice Try!"
        description = f"You guessed {number}, I was thinking of {secret_number}!"
    
    fact = random.choice(all_facts)
    
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\n🧠 **Bonus Fact:** {fact}",
        color=color
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='funfact', description='Get a fun fact about a specific topic!')
async def funfact_command(interaction: discord.Interaction, topic: str):
    topic_lower = topic.lower()
    
    topic_facts = {
        "space": ["A day on Venus is longer than its year", "The human nose can detect about 1 trillion different scents", "A single cloud can weigh more than a million pounds"],
        "ocean": ["A blue whale's heart is as big as a small car", "A shrimp's heart is in its head", "Sea otters hold hands while sleeping so they don't drift apart"],
        "food": ["Bananas are berries but strawberries aren't", "Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs", "Carrots were originally purple", "Cats can't taste sweetness"],
        "body": ["The human brain uses about 20% of the body's total energy", "The human nose can detect about 1 trillion different scents", "The tongue is the strongest muscle in the human body relative to its size", "Butterflies taste with their feet"],
        "time": ["Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid", "Oxford University is older than the Aztec Empire", "The shortest war in history lasted only 38-45 minutes"]
    }
    
    matching_facts = []
    for key, facts in topic_facts.items():
        if topic_lower in key or key in topic_lower:
            matching_facts.extend(facts)
    
    if not matching_facts:
        all_facts = []
        for category_facts in fact_categories.values():
            all_facts.extend(category_facts)
        fact = random.choice(all_facts)
        embed = discord.Embed(
            title="🤔 Couldn't find that topic...",
            description=f"But here's a random fact instead!\n\n{fact}",
            color=0x9b59b6
        )
    else:
        fact = random.choice(matching_facts)
        embed = discord.Embed(
            title=f"🧠 Fun Fact about {topic.title()}!",
            description=fact,
            color=0x3498db
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='random', description='Get a completely random interaction!')
async def random_command(interaction: discord.Interaction):
    random_actions = [
        "fact", "compliment", "joke", "challenge", "riddle", "tip"
    ]
    
    action = random.choice(random_actions)
    
    if action == "fact":
        all_facts = get_all_facts()
        fact = random.choice(all_facts)
        embed = discord.Embed(
            title="🎲 Random Fact!",
            description=fact,
            color=0x3498db
        )
    elif action == "compliment":
        compliments = [
            "You're absolutely fantastic!",
            "You have amazing taste in Discord bots!",
            "Your curiosity is inspiring!",
            "You're the reason I love sharing facts!",
            "You make learning fun!",
            "Your questions always brighten my day!"
        ]
        embed = discord.Embed(
            title="💝 Random Compliment!",
            description=random.choice(compliments),
            color=0xe91e63
        )
    elif action == "joke":
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "What do you call a fake noodle? An impasta!",
            "Why don't eggs tell jokes? They'd crack each other up!"
        ]
        embed = discord.Embed(
            title="😂 Random Joke!",
            description=random.choice(jokes),
            color=0xffeb3b
        )
    elif action == "challenge":
        challenges = [
            "Try to learn one new fact today!",
            "Share a fact with a friend!",
            "Look up something you've always wondered about!",
            "Ask me about a topic you're curious about!",
            "Try the trivia command and beat your score!"
        ]
        embed = discord.Embed(
            title="🎯 Random Challenge!",
            description=random.choice(challenges),
            color=0xff5722
        )
    elif action == "riddle":
        riddles = [
            "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I? (Answer: A map!)",
            "What has hands but cannot clap? (Answer: A clock!)",
            "What gets wetter the more it dries? (Answer: A towel!)",
            "What has keys but no locks? (Answer: A piano!)",
            "What can travel around the world while staying in a corner? (Answer: A stamp!)"
        ]
        embed = discord.Embed(
            title="🧩 Random Riddle!",
            description=random.choice(riddles),
            color=0x9c27b0
        )
    else:  # tip
        tips = [
            "Use `/categories` to see all available fact categories!",
            "Try `/guess [number]` for a fun guessing game!",
            "Use `/trivia` to test your knowledge!",
            "Check `/leaderboard` to see the top players!",
            "Use `/funfact [topic]` to get facts about specific topics!",
            "Try `!info` for detailed command information!",
            "Use `!stats` to see fact reaction statistics!"
        ]
        embed = discord.Embed(
            title="💡 Random Tip!",
            description=random.choice(tips),
            color=0x4caf50
        )
    
    await interaction.response.send_message(embed=embed)

def schedule_daily_facts():
    async def run_scheduler():
        while True:
            now = datetime.now()
            if now.hour == 9 and now.minute == 0:
                await send_daily_fact()
                await asyncio.sleep(60)
            await asyncio.sleep(30)
    
    asyncio.create_task(run_scheduler())

async def start_scheduler():
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            await send_daily_fact()
            await asyncio.sleep(60)
        await asyncio.sleep(30)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    content = message.content.lower()
    
    if bot.user in message.mentions:
        if 'fact' in content:
            all_facts = get_all_facts()
            fact = random.choice(all_facts)
            
            embed = discord.Embed(
                title="🧠 Fun Fact from BrainyJim!",
                description=fact,
                color=0x9b59b6
            )
            
            thumbs_up = fact_reactions[fact]['thumbs_up']
            thumbs_down = fact_reactions[fact]['thumbs_down']
            
            embed.add_field(name="Reactions", value=f"👍 {thumbs_up} | 👎 {thumbs_down}", inline=False)
            
            msg = await message.channel.send(embed=embed)
            try:
                await msg.add_reaction('👍')
                await msg.add_reaction('👎')
            except:
                pass
        
        elif 'hello' in content or 'hi' in content:
            greetings = [
                f"Hello there, {message.author.mention}! 🧠",
                f"Hi {message.author.mention}! Ready for some brain food? 🧠",
                f"Hey {message.author.mention}! What can I teach you today? 📚",
                f"Greetings, {message.author.mention}! Let's learn something new! ✨"
            ]
            await message.channel.send(random.choice(greetings))
        
        elif 'help' in content:
            embed = discord.Embed(
                title="🤖 BrainyJim Help",
                description="Here's what I can do for you!",
                color=0x2ecc71
            )
            embed.add_field(name="Slash Commands", value="`/fact` - Random fact\n`/categoryfact` - Category-specific fact\n`/trivia` - Play trivia\n`/guess` - Number guessing game\n`/funfact` - Topic-specific fact\n`/random` - Random interaction\n`/leaderboard` - See top players\n`/mystats` - Your stats\n`/categories` - View categories", inline=False)
            embed.add_field(name="Mention Commands", value="Just mention me and say 'fact', 'hello', or 'help'!", inline=False)
            embed.add_field(name="Text Commands", value="Use `!info` for detailed command info or `!stats` for statistics!", inline=False)
            await message.channel.send(embed=embed)
        
        elif 'thank' in content:
            thanks_responses = [
                "You're so welcome! 😊",
                "Happy to help! 🎉",
                "My pleasure! Keep learning! 📚",
                "Anytime! Knowledge is power! 💪",
                "You're awesome! 🌟"
            ]
            await message.channel.send(random.choice(thanks_responses))
        
        else:
            responses = [
                "I'm here to share amazing facts! Try `/fact` or just ask for a fact! 🧠",
                "Want to learn something cool? Use `/random` for a surprise! 🎲",
                "I love questions! Try `/trivia` to test your knowledge! 🎯",
                "Curious about something? Use `/funfact [topic]` to learn more! 🔍",
                "Say 'help' and I'll show you all my commands! Or use `!info` for details! 🤖"
            ]
            await message.channel.send(random.choice(responses))
    
    elif 'brainyjim' in content:
        responses = [
            "That's me! 🧠 What would you like to know?",
            "You called? Ready for some brain food! 🍎",
            "BrainyJim at your service! 🤖",
            "Hey there! Want to learn something awesome? 📚"
        ]
        await message.channel.send(random.choice(responses))
    
    await bot.process_commands(message)

@bot.command(name='stats')
async def stats_command(ctx):
    all_facts = get_all_facts()
    
    sorted_facts = sorted([(fact, reactions) for fact, reactions in fact_reactions.items() if fact in all_facts], 
                         key=lambda x: x[1]['thumbs_up'] - x[1]['thumbs_down'], reverse=True)
    
    embed = discord.Embed(
        title="📊 BrainyJim Fact Stats",
        color=0x2ecc71
    )
    
    top_facts = sorted_facts[:5]
    bottom_facts = sorted_facts[-5:]
    
    top_text = ""
    for i, (fact, reactions) in enumerate(top_facts, 1):
        score = reactions['thumbs_up'] - reactions['thumbs_down']
        top_text += f"{i}. {fact[:50]}... (Score: {score})\n"
    
    bottom_text = ""
    for i, (fact, reactions) in enumerate(bottom_facts, 1):
        score = reactions['thumbs_up'] - reactions['thumbs_down']
        bottom_text += f"{i}. {fact[:50]}... (Score: {score})\n"
    
    embed.add_field(name="🏆 Top Facts", value=top_text or "No data yet", inline=False)
    embed.add_field(name="📉 Bottom Facts", value=bottom_text or "No data yet", inline=False)
    
    total_players = len(user_scores)
    embed.add_field(name="🎯 Trivia Stats", value=f"Total players: {total_players}", inline=True)
    embed.add_field(name="📚 Database Stats", value=f"Total facts: {len(all_facts)}\nAPI facts: {len(api_facts_cache)}\nUser facts: {len(user_submitted_facts)}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='info')
async def info_command(ctx):
    embed = discord.Embed(
        title="🤖 BrainyJim - Your Smart Fact Bot!",
        description="I'm here to make learning fun and interactive! Here's everything I can do:",
        color=0x3498db
    )
    
    embed.add_field(
        name="🧠 Fact Commands",
        value="`/fact` - Get a random fun fact\n`/categoryfact [category]` - Get a fact from a specific category\n`/funfact [topic]` - Get facts about a topic\n`/categories` - See all available categories\n`/submitfact [fact]` - Submit your own fact\n`/morefacts` - Load more facts from APIs",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Interactive Games",
        value="`/trivia` - Play trivia (answer with reactions!)\n`/guess [number]` - Number guessing game\n`/random` - Surprise me with random content!",
        inline=False
    )
    
    embed.add_field(
        name="📊 Stats & Leaderboards",
        value="`/leaderboard` - See top trivia players\n`/mystats` - Check your personal stats\n`!stats` - See fact reaction statistics",
        inline=False
    )
    
    embed.add_field(
        name="💬 Chat with Me",
        value="Just mention me (@BrainyJim) and:\n• Say 'fact' for a random fact\n• Say 'hello' for a greeting\n• Say 'help' for this menu\n• Say 'thank you' for appreciation!",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Pro Tips",
        value="• React with 👍/👎 to rate facts\n• Use number reactions (1️⃣-4️⃣) for trivia\n• Try different categories: animals, science, history, random\n• I post daily facts at 9 AM!",
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for curious minds!")
    
    await ctx.send(embed=embed)

TOKEN= os.getenv('DISCORD_TOKEN')

if __name__=='__main__':
    if TOKEN:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("ERROR: Invalid Discord token! Check your DISCORD_TOKEN environment variable.")
        except discord.HTTPException as e:
            print(f"HTTP Error connecting to Discord: {e}")
        except Exception as error:
            print(f"Unexpected error starting bot: {error}")
    else:
        print("ERROR: DISCORD_TOKEN environment variable not set!")
        print("Please set your Discord bot token as an environment variable:")
        print("For Windows: set DISCORD_TOKEN=your_token_here")
        print("For Linux/Mac: export DISCORD_TOKEN=your_token_here")
