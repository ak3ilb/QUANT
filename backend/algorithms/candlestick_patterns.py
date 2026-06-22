import pandas as pd
import numpy as np

def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes top 15 candlestick patterns purely mathematically using vectorized operations.
    Returns the dataframe with a new column 'active_patterns' containing a comma-separated string
    of patterns detected on each row.
    """
    if len(df) == 0:
        return df

    # We make a copy to avoid mutating the original passed-in slice accidentally
    # if it's a view, though typically we pass a distinct DataFrame.
    df = df.copy()

    O = df['open'].values
    H = df['high'].values
    L = df['low'].values
    C = df['close'].values

    # Prevent division by zero
    hl_range = H - L
    hl_range = np.where(hl_range == 0, 1e-8, hl_range)
    
    body = np.abs(C - O)
    body_safe = np.where(body == 0, 1e-8, body)
    upper_shadow = H - np.maximum(O, C)
    lower_shadow = np.minimum(O, C) - L

    # Shifts for previous candles
    O_1 = np.roll(O, 1); O_1[0] = O[0]
    H_1 = np.roll(H, 1); H_1[0] = H[0]
    L_1 = np.roll(L, 1); L_1[0] = L[0]
    C_1 = np.roll(C, 1); C_1[0] = C[0]
    
    O_2 = np.roll(O, 2); O_2[:2] = O[:2]
    H_2 = np.roll(H, 2); H_2[:2] = H[:2]
    L_2 = np.roll(L, 2); L_2[:2] = L[:2]
    C_2 = np.roll(C, 2); C_2[:2] = C[:2]

    # Pattern definitions (Vectorized boolean arrays)

    # 1. Doji
    doji = body / hl_range < 0.1

    # 2. Hammer: bullish context (usually), small body, long lower shadow, small upper shadow
    hammer = (lower_shadow > 2 * body) & (upper_shadow < 0.2 * body) & (body > 0)

    # 3. Shooting Star: bearish context, long upper shadow, small lower shadow
    shooting_star = (upper_shadow > 2 * body) & (lower_shadow < 0.2 * body) & (body > 0)

    # 4. Bullish Engulfing
    bullish_engulfing = (C > O) & (C_1 < O_1) & (C > O_1) & (O < C_1)

    # 5. Bearish Engulfing
    bearish_engulfing = (C < O) & (C_1 > O_1) & (C < O_1) & (O > C_1)

    # 6. Morning Star: 3 candles (bearish, small body, bullish)
    # Candle 1: Strong Bear, Candle 2: Gap down & small body, Candle 3: Strong Bull pushing into C_1 body
    morning_star = (C_2 < O_2) & \
                   (np.abs(C_1 - O_1) / (H_1 - L_1 + 1e-8) < 0.3) & \
                   (C > O) & (C > (O_2 + C_2) / 2)

    # 7. Evening Star: 3 candles
    evening_star = (C_2 > O_2) & \
                   (np.abs(C_1 - O_1) / (H_1 - L_1 + 1e-8) < 0.3) & \
                   (C < O) & (C < (O_2 + C_2) / 2)

    # 8. Marubozu (Bullish): No shadows, big body
    marubozu_bull = (C > O) & (upper_shadow / body_safe < 0.05) & (lower_shadow / body_safe < 0.05)

    # 9. Marubozu (Bearish)
    marubozu_bear = (C < O) & (upper_shadow / body_safe < 0.05) & (lower_shadow / body_safe < 0.05)

    # 10. Harami (Bullish): Inside bar
    harami_bull = (C_1 < O_1) & (C > O) & (C < O_1) & (O > C_1)

    # 11. Harami (Bearish)
    harami_bear = (C_1 > O_1) & (C < O) & (C > O_1) & (O < C_1)

    # 12. Piercing Line: Bullish reversal
    piercing_line = (C_1 < O_1) & (C > O) & (O < C_1) & (C > (O_1 + C_1) / 2) & (C < O_1)

    # 13. Dark Cloud Cover: Bearish reversal
    dark_cloud_cover = (C_1 > O_1) & (C < O) & (O > C_1) & (C < (O_1 + C_1) / 2) & (C > O_1)

    # 14. Inverted Hammer: Bullish context shooting star
    inverted_hammer = shooting_star & (C_1 < O_1)  # occurs after a down candle

    # 15. Hanging Man: Bearish context hammer
    hanging_man = hammer & (C_1 > O_1)  # occurs after an up candle

    # Build the string array
    active_patterns = np.full(len(df), '', dtype=object)

    patterns = [
        ('doji', doji),
        ('hammer', hammer),
        ('shooting_star', shooting_star),
        ('engulfing_bull', bullish_engulfing),
        ('engulfing_bear', bearish_engulfing),
        ('morning_star', morning_star),
        ('evening_star', evening_star),
        ('marubozu_bull', marubozu_bull),
        ('marubozu_bear', marubozu_bear),
        ('harami_bull', harami_bull),
        ('harami_bear', harami_bear),
        ('piercing_line', piercing_line),
        ('dark_cloud_cover', dark_cloud_cover),
        ('inverted_hammer', inverted_hammer),
        ('hanging_man', hanging_man)
    ]

    for name, mask in patterns:
        # Avoid joining empty strings clumsily
        # If active_patterns is '', just set to name, else append ',name'
        idx = mask
        if not np.any(idx):
            continue
            
        current_vals = active_patterns[idx]
        new_vals = np.where(current_vals == '', name, current_vals + ',' + name)
        active_patterns[idx] = new_vals

    df['active_patterns'] = active_patterns
    return df
