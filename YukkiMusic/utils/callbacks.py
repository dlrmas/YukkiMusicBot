#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.
#
# Fix bug dan update https://github.com/dlrmas
#

"""
Helper functions for handling Telegram callback queries safely.
These functions prevent QUERY_ID_INVALID errors from cluttering logs.
"""


async def safe_answer(callback_query, text=None, show_alert=False):
    """
    Safely answer a callback query, ignoring expired queries.
    
    Args:
        callback_query: The CallbackQuery object
        text: Optional text to show in the answer
        show_alert: Whether to show as alert popup
    
    Returns:
        True if successful, False if failed
    """
    try:
        if text:
            await callback_query.answer(text, show_alert=show_alert)
        else:
            await callback_query.answer()
        return True
    except:
        return False


async def safe_edit_message(callback_query, text=None, reply_markup=None, **kwargs):
    """
    Safely edit a callback message, ignoring MESSAGE_NOT_MODIFIED errors.
    
    Args:
        callback_query: The CallbackQuery object
        text: New text for the message
        reply_markup: New reply markup
        **kwargs: Additional arguments for edit_message_text
    
    Returns:
        The edited message if successful, None if failed
    """
    try:
        if text:
            return await callback_query.edit_message_text(
                text, reply_markup=reply_markup, **kwargs
            )
        elif reply_markup:
            return await callback_query.edit_message_reply_markup(
                reply_markup=reply_markup
            )
    except:
        return None
