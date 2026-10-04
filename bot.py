import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import string
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "config.json"
REMINDER_FILE = "reminders.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["token"]

if os.path.exists(REMINDER_FILE):
    with open(REMINDER_FILE, "r", encoding="utf-8") as f:
        reminders = json.load(f)
else:
    reminders = []

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def save_reminders():
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=4)


def is_admin(interaction):
    return interaction.user.guild_permissions.administrator


async def send_reminder(reminder):
    channel = bot.get_channel(reminder["channel_id"])

    if channel is None:
        return

    try:
        await channel.send(reminder["message"])
    except discord.HTTPException:
        pass


@tasks.loop(seconds=30)
async def reminder_loop():
    now = datetime.now(timezone.utc)

    changed = False

    for reminder in reminders:
        try:
            next_time = datetime.fromisoformat(
                reminder["next_time"]
            )

            if now >= next_time:
                await send_reminder(reminder)

                next_time = next_time + timedelta(
                    seconds=reminder["interval"]
                )

                while next_time <= now:
                    next_time = next_time + timedelta(
                        seconds=reminder["interval"]
                    )

                reminder["next_time"] = next_time.isoformat()
                changed = True

        except Exception as e:
            print("리마인더 오류:", e)

    if changed:
        save_reminders()


@reminder_loop.before_loop
async def before_reminder_loop():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    if not reminder_loop.is_running():
        reminder_loop.start()

    try:
        synced = await bot.tree.sync()
        print(f"로그인 완료: {bot.user}")
        print(f"슬래시 명령어 {len(synced)}개 동기화 완료")
    except Exception as e:
        print("명령어 동기화 실패:", e)


@bot.tree.command(
    name="채널생성",
    description="지정된 이름의 채널을 생성합니다."
)
@app_commands.describe(
    종류="채널 종류",
    카테고리="채널을 넣을 카테고리"
)
@app_commands.choices(
    종류=[
        app_commands.Choice(name="텍스트", value="text"),
        app_commands.Choice(name="음성", value="voice")
    ]
)
async def create_channel(
    interaction,
    종류: app_commands.Choice[str],
    카테고리: discord.CategoryChannel = None
):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "채널 관리 권한이 필요합니다.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    names = [
        "tangodowninthenameof김태윤",
        "tangodowninthenameof카와이",
        "tangodowninthenameof천축",
        "tangodowninthenameof알라봉",
        "tangodowninthenameof판치르",
        "tangodowninthenameof수호이",
        "tangodowninthenameof사르마트",
        "tangodowninthenameof아방가르드"
    ]

    channels = []

    for name in names:
        for i in range(10):
            if 종류.value == "text":
                channel = await interaction.guild.create_text_channel(
                    name=name,
                    category=카테고리,
                    reason=f"Created by {interaction.user}"
                )
            else:
                channel = await interaction.guild.create_voice_channel(
                    name=name,
                    category=카테고리,
                    reason=f"Created by {interaction.user}"
                )

            channels.append(channel)

    await interaction.followup.send(
        f"채널 {len(channels)}개 생성 완료.",
        ephemeral=True
    )


@bot.tree.command(
    name="에브핑",
    description="@everyone을 멘션하고 지정한 메시지를 반복해서 전송합니다."
)
@app_commands.describe(
    메시지="전송할 메시지",
    횟수="메시지를 보낼 횟수"
)
async def everyone_ping(
    interaction,
    메시지: str,
    횟수: app_commands.Range[int, 1, 10000]
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    for i in range(횟수):
        await interaction.channel.send(
            f"@everyone {메시지}",
            allowed_mentions=discord.AllowedMentions(
                everyone=True
            )
        )

    await interaction.followup.send(
        f"에브핑 {횟수}회 전송 완료.",
        ephemeral=True
    )


@bot.tree.command(
    name="리마인더",
    description="지정한 시간마다 메시지를 반복 전송합니다."
)
@app_commands.describe(
    메시지="반복해서 보낼 메시지",
    간격="반복 간격",
    단위="시간 단위"
)
@app_commands.choices(
    단위=[
        app_commands.Choice(name="초", value="second"),
        app_commands.Choice(name="분", value="minute"),
        app_commands.Choice(name="시간", value="hour"),
        app_commands.Choice(name="일", value="day")
    ]
)
async def reminder(
    interaction,
    메시지: str,
    간격: app_commands.Range[int, 1, 365],
    단위: app_commands.Choice[str]
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    multipliers = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400
    }

    seconds = 간격 * multipliers[단위.value]

    next_time = datetime.now(timezone.utc) + timedelta(
        seconds=seconds
    )

    reminder_data = {
        "id": len(reminders) + 1,
        "guild_id": interaction.guild.id,
        "channel_id": interaction.channel.id,
        "message": 메시지,
        "interval": seconds,
        "next_time": next_time.isoformat(),
        "created_by": interaction.user.id
    }

    reminders.append(reminder_data)
    save_reminders()

    await interaction.response.send_message(
        f"리마인더 등록 완료.\n"
        f"{간격}{단위.name}마다 이 채널에 메시지를 전송합니다.\n"
        f"ID: `{reminder_data['id']}`",
        ephemeral=True
    )


@bot.tree.command(
    name="리마인더목록",
    description="현재 등록된 리마인더를 확인합니다."
)
async def reminder_list(interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    guild_reminders = [
        r for r in reminders
        if r["guild_id"] == interaction.guild.id
    ]

    if not guild_reminders:
        await interaction.response.send_message(
            "등록된 리마인더가 없습니다.",
            ephemeral=True
        )
        return

    text = []

    for r in guild_reminders:
        text.append(
            f"`{r['id']}` | <#{r['channel_id']}> | "
            f"{r['message']} | {r['interval']}초 간격"
        )

    await interaction.response.send_message(
        "\n".join(text),
        ephemeral=True
    )


@bot.tree.command(
    name="리마인더삭제",
    description="리마인더를 삭제합니다."
)
@app_commands.describe(아이디="삭제할 리마인더 ID")
async def reminder_delete(interaction, 아이디: int):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    for r in reminders:
        if (
            r["id"] == 아이디
            and r["guild_id"] == interaction.guild.id
        ):
            reminders.remove(r)
            save_reminders()

            await interaction.response.send_message(
                "리마인더 삭제 완료.",
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        "해당 리마인더를 찾을 수 없습니다.",
        ephemeral=True
    )


@bot.tree.command(
    name="고스트메시지",
    description="메시지를 보내고 즉시 삭제하는 것을 반복합니다."
)
@app_commands.describe(
    메시지="보냈다가 삭제할 메시지. 에브핑을 넣는것을 권장드립니다",
    횟수="반복 횟수",
    간격="메시지 사이 간격(초)"
)
async def ghost_message(
    interaction,
    메시지: str,
    횟수: app_commands.Range[int, 1, 100],
    간격: app_commands.Range[float, 0.5, 10.0]
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"고스트메시지 시작. {횟수}회 반복합니다.",
        ephemeral=True
    )

    for i in range(횟수):
        try:
            msg = await interaction.channel.send(메시지)
            await msg.delete()
        except discord.HTTPException:
            break

        if i < 횟수 - 1:
            await discord.utils.sleep_until(
                datetime.now(timezone.utc) + timedelta(
                    seconds=간격
                )
            )


@bot.tree.command(
    name="디엠",
    description="지정한 사용자에게 DM을 보냅니다."
)
@app_commands.describe(
    사용자="DM을 받을 사용자",
    메시지="보낼 메시지"
)
async def send_dm(
    interaction,
    사용자: discord.Member,
    메시지: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    try:
        await 사용자.send(메시지)

        await interaction.response.send_message(
            f"{사용자.mention}에게 DM 전송 완료.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "DM을 보낼 수 없습니다. 상대방이 서버 멤버 DM을 막아놨거나 봇 DM을 차단했을 수 있습니다.",
            ephemeral=True
        )


@bot.tree.command(
    name="멤버추방",
    description="지정한 멤버를 서버에서 추방합니다."
)
@app_commands.describe(
    사용자="추방할 멤버",
    사유="추방 사유"
)
async def kick_member(
    interaction,
    사용자: discord.Member,
    사유: str = "사유 없음"
):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(
            "멤버 추방 권한이 필요합니다.", ephemeral=True
        )
        return

    if 사용자 == interaction.guild.owner:
        await interaction.response.send_message(
            "서버 소유자는 추방할 수 없습니다.", ephemeral=True
        )
        return

    if 사용자.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "봇보다 높거나 같은 역할을 가진 멤버는 추방할 수 없습니다.", ephemeral=True
        )
        return

    if 사용자 == interaction.user:
        await interaction.response.send_message(
            "자기 자신은 추방할 수 없습니다.", ephemeral=True
        )
        return

    try:
        await 사용자.kick(reason=사유)
        await interaction.response.send_message(
            f"{사용자} 추방 완료.\n사유: {사유}", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "봇에게 멤버 추방 권한이 없거나 역할 순위가 부족합니다.", ephemeral=True
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"추방 중 오류가 발생했어.\n{e}", ephemeral=True
        )


@bot.tree.command(
    name="전체멤버추방",
    description="서버의 추방 가능한 멤버를 전부 추방합니다."
)
@app_commands.describe(
    확인="실행하려면 '확인'을 입력하세요"
)
async def kick_all_members(
    interaction,
    확인: str
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "관리자만 사용할 수 있습니다.", ephemeral=True
        )
        return

    if 확인 != "확인":
        await interaction.response.send_message(
            "실행하려면 확인 칸에 `확인`을 정확히 입력해야 합니다.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        "전체 멤버 추방을 시작합니다. 추방할 수 없는 멤버는 건너뜁니다.",
        ephemeral=True
    )

    me = interaction.guild.me
    success = 0
    fail = 0

    for member in list(interaction.guild.members):
        if member == me or member == interaction.guild.owner:
            continue
        if member.top_role >= me.top_role:
            fail += 1
            continue
        try:
            await member.kick(reason=f"전체 멤버 추방 - {interaction.user}")
            success += 1
        except (discord.Forbidden, discord.HTTPException):
            fail += 1

    try:
        await interaction.user.send(
            f"전체 멤버 추방 완료. 성공: {success}명 / 실패 또는 제외: {fail}명"
        )
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="채널전체삭제",
    description="서버의 모든 채널을 삭제합니다."
)
@app_commands.describe(
    확인="실행하려면 '확인'을 입력하세요"
)
async def delete_all_channels(
    interaction,
    확인: str
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "관리자만 사용할 수 있어.", ephemeral=True
        )
        return

    if 확인 != "확인":
        await interaction.response.send_message(
            "실행하려면 확인 칸에 `확인`을 정확히 입력해야 합니다.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        "전체 채널 삭제를 시작합니다.", ephemeral=True
    )

    channels = list(interaction.guild.channels)
    channels.sort(key=lambda c: isinstance(c, discord.CategoryChannel))
    success = 0
    fail = 0

    for channel in channels:
        try:
            await channel.delete(reason=f"전체 채널 삭제 - {interaction.user}")
            success += 1
        except (discord.Forbidden, discord.HTTPException):
            fail += 1

    try:
        await interaction.user.send(
            f"전체 채널 삭제 완료. 성공: {success}개 / 실패: {fail}개"
        )
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="역할생성",
    description="새로운 역할을 생성합니다."
)
@app_commands.describe(
    이름="생성할 역할 이름"
)
async def create_role(
    interaction,
    이름: str
):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "역할 관리 권한이 필요합니다.", ephemeral=True
        )
        return

    try:
        role = await interaction.guild.create_role(
            name=이름,
            reason=f"역할 생성 - {interaction.user}"
        )
        await interaction.response.send_message(
            f"역할 생성 완료: {role.mention}", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "봇에게 역할 관리 권한이 없습니다.", ephemeral=True
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"역할 생성 중 오류가 발생했습니다.\n{e}", ephemeral=True
        )


@bot.tree.command(
    name="전체역할부여",
    description="서버의 모든 멤버에게 지정한 역할을 부여합니다."
)
@app_commands.describe(
    역할="부여할 역할"
)
async def give_role_all(
    interaction,
    역할: discord.Role
):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "역할 관리 권한이 필요합니다.", ephemeral=True
        )
        return

    if 역할 >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "봇보다 높거나 같은 역할은 관리할 수 없습니다.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    success = 0
    fail = 0

    for member in interaction.guild.members:
        if member.bot:
            continue
        try:
            if 역할 not in member.roles:
                await member.add_roles(역할, reason=f"전체 역할 부여 - {interaction.user}")
                success += 1
        except (discord.Forbidden, discord.HTTPException):
            fail += 1

    await interaction.followup.send(
        f"역할 부여 완료. 성공: {success}명 / 실패: {fail}명",
        ephemeral=True
    )


@bot.tree.command(
    name="전체역할제거",
    description="서버의 모든 멤버에게서 지정한 역할을 제거합니다."
)
@app_commands.describe(
    역할="제거할 역할"
)
async def remove_role_all(
    interaction,
    역할: discord.Role
):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "역할 관리 권한이 필요합니다.", ephemeral=True
        )
        return

    if 역할 >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "봇보다 높거나 같은 역할은 관리할 수 없습니다.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    success = 0
    fail = 0

    for member in interaction.guild.members:
        if member.bot:
            continue
        try:
            if 역할 in member.roles:
                await member.remove_roles(역할, reason=f"전체 역할 제거 - {interaction.user}")
                success += 1
        except (discord.Forbidden, discord.HTTPException):
            fail += 1

    await interaction.followup.send(
        f"역할 제거 완료. 성공: {success}명 / 실패: {fail}명",
        ephemeral=True
    )


bot.run(TOKEN)
