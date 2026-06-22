"""FinRL CryptoEnv — gymnasium-compatible cryptocurrency trading environment."""
from __future__ import annotations

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    gym = None
    spaces = None


class CryptoTradingEnv:
    """
    FinRL env_multiple_crypto.CryptoEnv logic.
    Works standalone or wrapped as gymnasium.Env via make_gym_env().
    """

    def __init__(
        self,
        config: dict,
        lookback: int = 1,
        initial_capital: float = 1e6,
        buy_cost_pct: float = 1e-3,
        sell_cost_pct: float = 1e-3,
        gamma: float = 0.99,
        include_turbulence_state: bool = False,
    ):
        self.lookback = lookback
        self.include_turbulence_state = include_turbulence_state
        self.initial_cash = initial_capital
        self.buy_cost_pct = buy_cost_pct
        self.sell_cost_pct = sell_cost_pct
        self.gamma = gamma
        self.price_array = np.asarray(config["price_array"], dtype=np.float32)
        self.tech_array = np.asarray(config["tech_array"], dtype=np.float32)
        self.turbulence_array = np.asarray(config.get("turbulence_array", np.zeros(self.price_array.shape[0])))
        self.if_train = config.get("if_train", True)

        self.crypto_num = self.price_array.shape[1]
        self.max_step = self.price_array.shape[0] - lookback - 1
        self._generate_action_normalizer()

        self.time = lookback - 1
        self.cash = self.initial_cash
        self.stocks = np.zeros(self.crypto_num, dtype=np.float32)
        self.total_asset = self.cash + (self.stocks * self.price_array[self.time]).sum()
        self.gamma_return = 0.0
        self.episode_return = 1.0

        turb_dims = 2 if include_turbulence_state else 0
        self.state_dim = 1 + (self.price_array.shape[1] + self.tech_array.shape[1]) * lookback + turb_dims
        self.action_dim = self.crypto_num
        self.if_discrete = False

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)
        self.time = self.lookback - 1
        self.cash = self.initial_cash
        self.stocks = np.zeros(self.crypto_num, dtype=np.float32)
        self.total_asset = self.cash + (self.stocks * self.price_array[self.time]).sum()
        self.gamma_return = 0.0
        return self.get_state(), {}

    def step(self, actions):
        self.time += 1
        price = self.price_array[self.time]
        actions = np.asarray(actions, dtype=np.float32).flatten()
        actions = actions * self.action_norm_vector

        for index in np.where(actions < 0)[0]:
            if price[index] > 0:
                sell = min(self.stocks[index], -actions[index])
                self.stocks[index] -= sell
                self.cash += price[index] * sell * (1 - self.sell_cost_pct)

        for index in np.where(actions > 0)[0]:
            if price[index] > 0:
                buy = min(self.cash // (price[index] * (1 + self.buy_cost_pct)), actions[index])
                self.stocks[index] += buy
                self.cash -= price[index] * buy * (1 + self.buy_cost_pct)

        done = self.time >= self.max_step
        state = self.get_state()
        next_total = self.cash + (self.stocks * self.price_array[self.time]).sum()
        reward = (next_total - self.total_asset) * 2**-16
        self.total_asset = next_total
        self.gamma_return = self.gamma_return * self.gamma + reward
        if done:
            reward = self.gamma_return
            self.episode_return = self.total_asset / self.initial_cash
        return state, float(reward), done, False, {"total_asset": self.total_asset, "episode_return": self.episode_return}

    def get_state(self):
        state = np.hstack((self.cash * 2**-18, self.stocks * 2**-3))
        for i in range(self.lookback):
            tech_i = self.tech_array[self.time - i]
            state = np.hstack((state, tech_i * 2**-15))
        turb = float(self.turbulence_array[self.time]) if len(self.turbulence_array) > self.time else 0.0
        if self.include_turbulence_state:
            turb_flag = 1.0 if turb > 0 else 0.0
            state = np.hstack((state, np.array([turb * 2**-7, turb_flag], dtype=np.float32)))
        return state.astype(np.float32)

    def _generate_action_normalizer(self):
        vectors = []
        for price in self.price_array[0]:
            x = len(str(price)) - 7
            vectors.append(1 / (10**x))
        self.action_norm_vector = np.asarray(vectors, dtype=np.float32)


if gym is not None:

    class GymCryptoEnv(gym.Env):
        """Gymnasium wrapper for stable-baselines3."""

        metadata = {"render_modes": []}

        def __init__(self, config: dict, **kwargs):
            super().__init__()
            self._env = CryptoTradingEnv(config, **kwargs)
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(self._env.state_dim,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=-1, high=1, shape=(self._env.action_dim,), dtype=np.float32
            )

        def reset(self, *, seed=None, options=None):
            obs, info = self._env.reset(seed=seed, options=options)
            return obs, info

        def step(self, action):
            obs, reward, terminated, truncated, info = self._env.step(action)
            return obs, reward, terminated, truncated, info


def make_gym_env(config: dict, **kwargs):
    if gym is None:
        raise ImportError("gymnasium required for DRL training: pip install -r requirements-rl.txt")
    return GymCryptoEnv(config, **kwargs)
