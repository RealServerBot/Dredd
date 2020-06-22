"""
Dredd, discord bot
Copyright (C) 2020 Moksej
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import discord
import datetime
import re
from discord.ext import commands
from utils import default
from datetime import datetime
from db import emotes

CAPS = re.compile(r"[ABCDEFGHIJKLMNOPQRSTUVWXYZ]")
LINKS = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
INVITE = re.compile(r"(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?")


class logs(commands.Cog, name="Logs", command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def get_audit_logs(self, guild, limit=100, user=None, action=None):
        return await self.bot.get_guild(guild.id).audit_logs(limit=limit, user=user, action=action).flatten()


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        if before.guild is None:
            return

        db_check = await self.bot.db.fetchval("SELECT guild_id FROM msgedit WHERE guild_id = $1", before.guild.id)
        lchannels = await self.bot.db.fetchval("SELECT channel_id FROM msgedit WHERE guild_id = $1", before.guild.id)

        if db_check is None:
            return

        if before.author.bot:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_msgedit} Message edited! [Jump to message]({before.jump_url})",
                              timestamp=datetime.utcnow())
        embed.set_author(icon_url=before.author.avatar_url, name=before.author)
        embed.add_field(name="From:", value=f"{before.content}", inline=True)
        embed.add_field(name="To:", value=f"{after.content}", inline=False)
        embed.add_field(name="Channel:",
                         value=f"{before.channel.mention}", inline=True)

        lchannel = before.guild.get_channel(lchannels)
        try:
            await lchannel.send(embed=embed)
        except:
            pass

# ~ End


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        embed = discord.Embed(
            color=self.bot.logging_color, description=f"{emotes.log_msgdelete} Message deleted!", timestamp=datetime.utcnow())
        embed.set_author(icon_url=message.author.avatar_url, name=message.author)
        embed.add_field(name="Message:", value=message.content, inline=False)
        embed.add_field(name="Channel:",
                        value=message.channel.mention)
        

        embed.set_footer(text=f"ID: {message.id}")

        db_check = await self.bot.db.fetchval("SELECT guild_id FROM msgdelete WHERE guild_id = $1", message.guild.id)
        channels = await self.bot.db.fetchval("SELECT channel_id FROM msgdelete WHERE guild_id = $1", message.guild.id)

        if db_check is None:
            return

        channel = message.guild.get_channel(channels)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        #print(f'{member} has joined a server ({member.guild}).')

        # ! Join role (Role on join)
        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM joinrole WHERE guild_id = $1", member.guild.id)
        peoplerole = await self.bot.db.fetchval("SELECT role_id FROM joinrole WHERE guild_id = $1", member.guild.id)
        botrole = await self.bot.db.fetchval("SELECT bots FROM joinrole WHERE guild_id = $1", member.guild.id)
        # ! Join log (Member join log)
        db_check2 = await self.bot.db.fetchval("SELECT guild_id FROM joinlog WHERE guild_id = $1", member.guild.id)
        joinlog = await self.bot.db.fetchval("SELECT channel_id FROM joinlog WHERE guild_id = $1", member.guild.id)
        # ! Join message (Welcome msg)
        db_check3 = await self.bot.db.fetchval("SELECT guild_id FROM joinmsg WHERE guild_id = $1", member.guild.id)
        joinmsg = await self.bot.db.fetchval("SELECT channel_id FROM joinmsg WHERE guild_id = $1", member.guild.id)
        message = await self.bot.db.fetchval("SELECT msg FROM joinmsg WHERE guild_id = $1", member.guild.id)
        bots = await self.bot.db.fetchval("SELECT bot_join FROM joinmsg WHERE guild_id = $1", member.guild.id)
        # ! Temp mute
        temp_mute = await self.bot.db.fetchval("SELECT user_id FROM moddata WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)

                   

        if db_check1 is not None:
            if member.guild.me.guild_permissions.manage_roles:
                # Role on join
                if member.bot:
                    role = member.guild.get_role(botrole)
                    await member.add_roles(role, reason='Autorole')
                elif not member.bot:
                    role = member.guild.get_role(peoplerole)
                    await member.add_roles(role, reason='Autorole')
                    # if member.guild.id == 671078170874740756:
                    #     roles = member.guild.get_role(679642623107137549)
                    #     await member.add_roles(roles)
                if temp_mute:
                    muterole = discord.utils.find(lambda r: r.name.lower() == "muted", member.guild.roles)
                    await member.add_roles(muterole, reason='User was muted before')
        if db_check3 is not None:
            if member.bot and bots == False:
                return
            elif member.bot and bots == True:
                pass
            elif bots is None:
                pass
            if message:
                joinmessage = str(message)
                joinmessage = joinmessage.replace("::member.mention::", member.mention)
                joinmessage = joinmessage.replace("::member.name::", member.name)
                joinmessage = joinmessage.replace("::server.name::", member.guild.name)
                joinmessage = joinmessage.replace("::server.members::", str(member.guild.member_count))
            elif message is None:
                joinmessage = f"{emotes.joined} {member.mention} joined the server! There are {member.guild.member_count} members in the server now."
            # Welcome msg
            welcomechannel = self.bot.get_channel(joinmsg)
            await welcomechannel.send(joinmessage, allowed_mentions=discord.AllowedMentions(users=True))
        if db_check2 is not None:
            # Member join log
            logchannel = self.bot.get_channel(joinlog)
            embed = discord.Embed(
                color=self.bot.logging_color, description=f"{emotes.log_memberjoin} New member joined", timestamp=datetime.utcnow())
            #embed.set_author(icon_url=member.avatar_url)
            embed.add_field(name="Username:", value=member, inline=True)
            embed.add_field(name="User ID:", value=member.id, inline=True)
            embed.add_field(name="Created at:", value=default.date(
                member.created_at), inline=False)
            embed.set_thumbnail(url=member.avatar_url)
            await logchannel.send(embed=embed)

##############################
    @commands.Cog.listener()
    async def on_member_remove(self, member):

        await self.bot.db.execute("DELETE FROM warnings WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)
        await self.bot.db.execute("DELETE FROM autowarns WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)

        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM leavemsg WHERE guild_id = $1", member.guild.id)
        leavelog = await self.bot.db.fetchval("SELECT channel_id FROM leavemsg WHERE guild_id = $1", member.guild.id)
        message = await self.bot.db.fetchval("SELECT msg FROM leavemsg WHERE guild_id = $1", member.guild.id)
        bots = await self.bot.db.fetchval("SELECT bot_join FROM leavemsg WHERE guild_id = $1", member.guild.id)

        db_check2 = await self.bot.db.fetchval("SELECT guild_id FROM joinlog WHERE guild_id = $1", member.guild.id)
        joinlog = await self.bot.db.fetchval("SELECT channel_id FROM joinlog WHERE guild_id = $1", member.guild.id)

        moderation = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", member.guild.id)

        case = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", member.guild.id)

        if member.guild.me.guild_permissions.view_audit_log:
            checks = await self.get_audit_logs(member.guild, limit=1, action=discord.AuditLogAction.kick)  

        if db_check1 is not None:
            if member.bot and bots == False:
                return
            elif member.bot and bots == True:
                pass
            elif bots is None:
                pass
            if message:
                leavemessage = str(message)
                leavemessage = leavemessage.replace("::member.mention::", member.mention)
                leavemessage = leavemessage.replace("::member.name::", member.name)
                leavemessage = leavemessage.replace("::server.name::", member.guild.name)
                leavemessage = leavemessage.replace("::server.members::", str(member.guild.member_count))
            elif message is None:
                leavemessage = f"{emotes.left} {member.mention} left the server... There are {member.guild.member_count} members left in the server."

            leavechannel = self.bot.get_channel(leavelog)
            await leavechannel.send(leavemessage, allowed_mentions=discord.AllowedMentions(users=True))

        if db_check2 is not None:
            # Member leave log
            logchannel = self.bot.get_channel(joinlog)
            embed = discord.Embed(
                color=self.bot.logging_color, description=f"{emotes.log_memberleave} Member left", timestamp=datetime.utcnow())
            #embed.set_author(icon_url=member.avatar_url)
            embed.add_field(name="Username:", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Created at:", value=default.date(
                member.created_at), inline=False)
            embed.add_field(name="Joined at:", value=default.date(member.joined_at), inline=False)
            embed.set_thumbnail(url=member.avatar_url)
            await logchannel.send(embed=embed)

        if moderation is not None:
            try:
                deleted = ""
                async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                    deleted += f"{entry.user} ({entry.user.id})"
                    #print(entry)
            except Exception as e:
                print(e)
                pass
            logchannel = self.bot.get_channel(moderation)
            if deleted and (datetime.utcnow() - checks[0].created_at).total_seconds() < 5:
                if case is None:
                    await self.bot.db.execute("INSERT INTO modlog(guild_id, case_num) VALUES ($1, $2)", member.guild.id, 1)

                casenum = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", member.guild.id)
                embed = discord.Embed(
                    color=self.bot.logging_color, description=f"{emotes.log_memberleave} Member kicked `[#{casenum}]`", timestamp=datetime.utcnow())
                #embed.set_author(icon_url=member.avatar_url)
                embed.add_field(name="Username:", value=f"{member} ({member.id})", inline=True)
                embed.add_field(name="Created at:", value=default.date(
                    member.created_at), inline=False)
                embed.add_field(name="Joined at:", value=default.date(member.joined_at), inline=False)
                embed.add_field(name='Moderator:', value=deleted, inline=False)
                embed.set_thumbnail(url=member.avatar_url)
                await self.bot.db.execute("UPDATE modlog SET case_num = case_num + 1 WHERE guild_id = $1", member.guild.id)
                return await logchannel.send(embed=embed)

            elif deleted and (datetime.utcnow() - checks[0].created_at).total_seconds() > 5:
                return


        

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot:
            return

        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM memberupdate WHERE guild_id = $1", before.guild.id)
        logchannel = await self.bot.db.fetchval("SELECT channel_id FROM memberupdate WHERE guild_id = $1", before.guild.id)
        if before.nick != after.nick:
            if before.nick is None:
                nick = before.name
            elif before.nick:
                nick = before.nick
            await self.bot.db.execute("INSERT INTO nicknames(user_id, guild_id, nickname, time) VALUES ($1, $2, $3, $4)", before.id, before.guild.id, nick, datetime.utcnow())

        if db_check1 is None:
            return
        
        if before.nick is None:
            nick = before.name
        elif before.nick:
            nick = before.nick
        if after.nick is None:
            nicks = after.name
        elif after.nick:
            nicks = after.nick

        channel = self.bot.get_channel(logchannel)

        if before.nick != after.nick:
            try:
                deleted = ""
                async for entry in before.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
                    deleted += f"{entry.user} ({entry.user.id})"
            except Exception as e:
                print(e)
                deleted = "Fail"
            e = discord.Embed(
                color=self.bot.logging_color,description=f"{emotes.log_memberedit} Nickname changed", timestamp=datetime.utcnow())
            e.set_author(name="Nickname changed", icon_url=before.avatar_url)
            e.add_field(name="User:", value=f"{after.name}\n({after.id})")
            e.add_field(name="Nickname:",
                        value=f"{nick} → {nicks}")
            if deleted:
                e.add_field(name="Changed by:", value=deleted, inline=False)
            e.set_thumbnail(url=after.avatar_url)
            e.set_footer(text=f'User ID: {after.id}')
            await channel.send(embed=e)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        # Don't listen to bots
        if before.bot:
            return

        
        for guild in self.bot.guilds:
            if before in guild.members:
                db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM memberupdate WHERE guild_id = $1", guild.id)
                logchannel = await self.bot.db.fetchval("SELECT channel_id FROM memberupdate WHERE guild_id = $1", guild.id)
                
                if db_check1 is None:
                    return
                    
                channel = self.bot.get_channel(logchannel)

                # Avatar changed
                if before.avatar != after.avatar:
                    e = discord.Embed(color=self.bot.logging_color,
                                              title=f"{emotes.log_memberedit} Avatar updated",
                                              timestamp=datetime.utcnow())
                    #e.set_author(name=after, icon_url=after.avatar_url)
                    e.description = f"**{after.name}** has changed his avatar"
                    e.set_thumbnail(url=after.avatar_url)
                    #e.set_image(url=before.avatar_url)
                    e.set_footer(text=f"User ID: {after.id}")
                    await channel.send(embed=e)
                            
                # Username changed
                if before.name != after.name:
                    e = discord.Embed(color=self.bot.logging_color, title=f"{emotes.log_memberedit} Username updated", description=f"**{before.name}** changed his username to **{after.name}**", timestamp=datetime.utcnow())
                    #e.set_author(name=after, icon_url=after.avatar_url)
                    e.set_footer(text=f"User ID: {after.id}")
                    await channel.send(embed=e)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):

        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM moderation WHERE guild_id = $1", guild.id)
        logchannel = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", guild.id)
        case = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", guild.id)

        if logchannel is not None:
            channel = self.bot.get_channel(logchannel)

        if db_check1 is None:
            return
        
        if case is None:
            await self.bot.db.execute("INSERT INTO modlog(guild_id, case_num) VALUES ($1, $2)", guild.id, 1)
        
        try:
            deleted = ""
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                deleted += f"{entry.user} ({entry.user.id})"
        except Exception as e:
            print(e)
            pass

        casenum = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", guild.id)

        embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_ban} Member banned! `[#{casenum}]`",
                              timestamp=datetime.utcnow())
        embed.add_field(name="Member:",
                        value=f'{user} ({user.id})', inline=True)
        embed.add_field(name="Member created at:", value=default.date(user.created_at), inline=True)
        if deleted:
            embed.add_field(name="Moderator:", value=deleted)
        embed.set_thumbnail(url=user.avatar_url)
        await self.bot.db.execute("UPDATE modlog SET case_num = case_num + 1 WHERE guild_id = $1", guild.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):

        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM moderation WHERE guild_id = $1", guild.id)
        logchannel = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", guild.id)
        case = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", guild.id)

        channel = self.bot.get_channel(logchannel)

        if db_check1 is None:
            return

        if case is None:
            await self.bot.db.execute("INSERT INTO modlog(guild_id, case_num) VALUES ($1, $2)", guild.id, 1)

        try:
            deleted = ""
            async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
                deleted += f"{entry.user} ({entry.user.id})"
        except Exception as e:
            print(e)
            pass

        casenum = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", guild.id)

        embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_unban} Member unbanned! `[#{casenum}]`",
                              timestamp=datetime.utcnow())
        embed.add_field(name="User name",
                        value=f'{user} ({user.id})', inline=True)
        embed.add_field(name="Member created at:", value=default.date(user.created_at), inline=True)
        if deleted:
            embed.add_field(name="Moderator", value=deleted)
        embed.set_thumbnail(url=user.avatar_url)
        await self.bot.db.execute("UPDATE modlog SET case_num = case_num + 1 WHERE guild_id = $1", guild.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM moderation WHERE guild_id = $1", member.guild.id)
        logchannel = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", member.guild.id)
        case = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", member.guild.id)

        channel = self.bot.get_channel(logchannel)

        if db_check1 is None:
            return

        if case is None:
            await self.bot.db.execute("INSERT INTO modlog(guild_id, case_num) VALUES ($1, $2)", member.guild.id, 1)

        try:
            deleted = ""
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
                deleted += f"{entry.user} ({entry.user.id})"
        except Exception as e:
            print(e)
            pass

        casenum = await self.bot.db.fetchval("SELECT case_num FROM modlog WHERE guild_id = $1", member.guild.id)
        
        if before.mute != after.mute:
            if after.mute is False:
                mt = "unmuted"
            elif after.mute is True:
                mt = "muted"
            embed = discord.Embed(color=self.bot.logging_color,
                                description=f"{emotes.log_memberedit} Member was voice {mt}! `[#{casenum}]`",
                                timestamp=datetime.utcnow())
            embed.add_field(name="User:",
                            value=f'{member} ({member.id})', inline=True)
            if deleted:
                embed.add_field(name="Moderator:", value=deleted)
            embed.set_thumbnail(url=member.avatar_url)
            await self.bot.db.execute("UPDATE modlog SET case_num = case_num + 1 WHERE guild_id = $1", member.guild.id)
            await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        db_check1 = await self.bot.db.fetchval("SELECT guild_id FROM moderation WHERE guild_id = $1", before.id)
        logchannel = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", before.id)

        channels = self.bot.get_channel(logchannel)

        if db_check1 is None:
            return

        
        if before.name != after.name:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild name was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="Name:", value=f"{before.name} → {after.name}")

            await channels.send(embed=embed)
        
        if before.region != after.region:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild region was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="Region:", value=f"{before.region} → {after.region}")

            await channels.send(embed=embed)
        
        if before.afk_channel != after.afk_channel:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild afk channel was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="AFK Channel:", value=f"{before.afk_channel} → {after.afk_channel}")

            await channels.send(embed=embed)
        
        if before.icon_url != after.icon_url:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild icon was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="Before:", value=f"[Old icon]({before.icon_url})")
            embed.set_thumbnail(url=after.icon_url)

            await channels.send(embed=embed)
        
        if before.mfa_level != after.mfa_level:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild multifactor authentication (MFA) was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="MFA level:", value=f"{before.mfa_level} → {after.mfa_level}")
            

            await channels.send(embed=embed)
        
        if before.verification_level != after.verification_level:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild verification level was changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="Verfication:", value=f"{before.verification_level} → {after.verification_level}")
            

            await channels.send(embed=embed)
        
        if before.default_notifications != after.default_notifications:
            embed = discord.Embed(color=self.bot.logging_color,
                              description=f"{emotes.log_guildupdate} Guild default notifications were changed!",
                              timestamp=datetime.utcnow())
            embed.add_field(name="Notifications:", value=f"{before.default_notifications.name} → {after.default_notifications.name}")

            await channels.send(embed=embed)


def setup(bot):
    bot.add_cog(logs(bot))
