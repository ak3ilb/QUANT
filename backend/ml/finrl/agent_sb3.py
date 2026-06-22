"""Stable-Baselines3 DRL agent (FinRL agents/stablebaselines3/models.py pattern)."""
from __future__ import annotations

import os

from ml.finrl import config

MODELS = {}
MODEL_KWARGS = config.MODEL_PARAMS


def _require_sb3():
    try:
        from stable_baselines3 import A2C, DDPG, PPO, SAC, TD3
        from stable_baselines3.common.vec_env import DummyVecEnv
    except ImportError as e:
        raise ImportError(
            "stable-baselines3 required: pip install -r requirements-rl.txt"
        ) from e
    return A2C, DDPG, PPO, SAC, TD3, DummyVecEnv


class DRLAgent:
    def __init__(self, env_factory):
        """
        env_factory: callable returning a gym.Env (fresh instance per vec env).
        """
        self.env_factory = env_factory

    def get_model(self, model_name: str, model_kwargs: dict | None = None):
        A2C, DDPG, PPO, SAC, TD3, DummyVecEnv = _require_sb3()
        models = {"a2c": A2C, "ddpg": DDPG, "td3": TD3, "sac": SAC, "ppo": PPO}
        name = model_name.lower()
        if name not in models:
            raise ValueError(f"Unknown model {model_name}; choose from {list(models)}")
        kwargs = dict(MODEL_KWARGS.get(name, {}))
        if model_kwargs:
            kwargs.update(model_kwargs)
        vec_env = DummyVecEnv([self.env_factory])
        tb_log = config.TENSORBOARD_LOG_DIR
        try:
            import tensorboard  # noqa: F401
        except ImportError:
            tb_log = None
        return models[name]("MlpPolicy", vec_env, verbose=1, tensorboard_log=tb_log, **kwargs)

    def train_model(self, model, total_timesteps: int, cwd: str | None = None) -> str:
        cwd = cwd or os.path.join(config.TRAINED_MODEL_DIR, "latest")
        os.makedirs(cwd, exist_ok=True)
        model.learn(total_timesteps=total_timesteps)
        path = os.path.join(cwd, "model.zip")
        model.save(path)
        return path

    @staticmethod
    def load_model(model_name: str, path: str):
        A2C, DDPG, PPO, SAC, TD3, _ = _require_sb3()
        models = {"a2c": A2C, "ddpg": DDPG, "td3": TD3, "sac": SAC, "ppo": PPO}
        name = model_name.lower()
        return models[name].load(path)

    @staticmethod
    def predict(env, model, deterministic: bool = True) -> dict:
        """Run one episode; return asset curve and return."""
        obs, _ = env.reset()
        done = False
        assets = [env._env.total_asset if hasattr(env, "_env") else env.total_asset]
        while not done:
            action, _ = model.predict(obs, deterministic=deterministic)
            step = env.step(action)
            if len(step) == 5:
                obs, _, terminated, truncated, info = step
                done = terminated or truncated
            else:
                obs, _, done, info = step
            total = info.get("total_asset") if isinstance(info, dict) else None
            if total is None:
                inner = env._env if hasattr(env, "_env") else env
                total = inner.total_asset
            assets.append(total)
        inner = env._env if hasattr(env, "_env") else env
        return {
            "episode_return": inner.episode_return,
            "final_asset": inner.total_asset,
            "assets": assets,
        }
