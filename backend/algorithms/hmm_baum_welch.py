import numpy as np
import pandas as pd
from hmmlearn import hmm

class HMMBaumWelch:
    def __init__(self):
        self.hmm_model = None

    def detect_regime(self, df: pd.DataFrame) -> dict:
        if len(df) < 50:
            return {"current_regime": "Unknown", "confidence": 0}
            
        returns = df['close'].pct_change().dropna().values.reshape(-1, 1)
        
        try:
            model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
            model.fit(returns)
            self.hmm_model = model
            
            hidden_states = model.predict(returns)
            means = model.means_.flatten()
            state_map = {
                np.argmax(means): "Bull",
                np.argmin(means): "Bear",
                list(set([0, 1, 2]) - set([np.argmax(means), np.argmin(means)]))[0]: "Sideways"
            }
            
            current_state = hidden_states[-1]
            current_regime = state_map[current_state]
            
            probs = model.predict_proba(returns)
            confidence = float(probs[-1][current_state])
            
            return {
                "current_regime": current_regime,
                "confidence": confidence,
                "means": means.tolist(),
                "transition_matrix": model.transmat_.tolist()
            }
        except Exception as e:
            try:
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
                states = kmeans.fit_predict(returns)
                centers = kmeans.cluster_centers_.flatten()
                sorted_idx = np.argsort(centers)
                state_map = {sorted_idx[0]: "Bear", sorted_idx[1]: "Sideways", sorted_idx[2]: "Bull"}
                
                return {
                    "current_regime": state_map[states[-1]],
                    "confidence": 0.5,
                    "note": "HMM failed, fallback to KMeans"
                }
            except:
                return {
                    "current_regime": "Sideways",
                    "confidence": 0,
                    "note": "All regime models failed"
                }
