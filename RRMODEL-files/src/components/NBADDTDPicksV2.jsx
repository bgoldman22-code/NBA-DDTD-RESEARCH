import React, { useState, useEffect } from 'react';

/**
 * NBA DD/TD Picks Component V2
 * Displays two tables:
 * 1. Recommended Picks (passing gates) with unit sizing
 * 2. All players >35% probability
 */

const NBADDTDPicksV2 = () => {
  const [picks, setPicks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPicks = async () => {
      try {
        setLoading(true);
        const response = await fetch('/.netlify/functions/nbaddtd-picks');
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setPicks(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching DD/TD picks:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPicks();
  }, []);

  // Helper to format American odds
  const formatOdds = (odds) => {
    if (!odds) return 'N/A';
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  // Helper to get edge color
  const getEdgeColor = (edge) => {
    if (!edge) return 'text-gray-500';
    if (edge >= 0.30) return 'text-green-600 font-bold';
    if (edge >= 0.20) return 'text-green-500 font-semibold';
    if (edge >= 0.10) return 'text-lime-500';
    if (edge >= 0.05) return 'text-yellow-500';
    return 'text-red-500';
  };

  // Helper to get probability color
  const getProbColor = (prob) => {
    if (prob >= 0.70) return 'text-green-600 font-bold';
    if (prob >= 0.50) return 'text-green-500';
    if (prob >= 0.35) return 'text-blue-500';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading DD/TD picks...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">
          <strong>Error loading picks:</strong> {error}
        </p>
        <p className="text-red-600 text-sm mt-2">
          Please try refreshing the page. If the problem persists, picks may not be available yet today.
        </p>
      </div>
    );
  }

  if (!picks || !picks.recommended_picks) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">No picks available for today.</p>
      </div>
    );
  }

  const { recommended_picks, high_probability, summary, date, generated_at, bankroll, unit_size } = picks;
  const allRecommended = [...(recommended_picks.dd || []), ...(recommended_picks.td || [])];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h2 className="text-2xl font-bold text-blue-900 mb-2">
          🏀 NBA Double-Double & Triple-Double Picks
        </h2>
        <div className="text-sm text-blue-700">
          <p><strong>Date:</strong> {date}</p>
          <p><strong>Generated:</strong> {new Date(generated_at).toLocaleString()}</p>
          <p><strong>Bankroll:</strong> ${bankroll?.toLocaleString()} | <strong>Unit Size:</strong> ${unit_size}</p>
          <p><strong>Model:</strong> V3 (Gradient Boosting + Isotonic Calibration)</p>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{summary.total_recommended_dd}</div>
            <div className="text-sm text-green-600">DD Picks</div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-700">{summary.total_recommended_td}</div>
            <div className="text-sm text-purple-600">TD Picks</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-700">{summary.total_recommended_units?.toFixed(1)}U</div>
            <div className="text-sm text-blue-600">Total Units</div>
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-orange-700">${summary.total_recommended_amount?.toFixed(0)}</div>
            <div className="text-sm text-orange-600">Total Amount</div>
          </div>
        </div>
      )}

      {/* Table 1: Recommended Picks */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-3">
          ⭐ Recommended Picks (Passing Acceptance Gates)
        </h3>
        
        {allRecommended.length === 0 ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-600">
            No picks passing acceptance gates today
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-300 rounded-lg">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Player</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Game</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Type</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Model %</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Odds</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Book</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Edge</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Bet</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Stats (L20)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {allRecommended.map((pick, idx) => {
                  const isDD = recommended_picks.dd?.includes(pick);
                  return (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{pick.player}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{pick.game}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          isDD ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'
                        }`}>
                          {isDD ? 'DD' : 'TD'}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-center font-semibold ${getProbColor(pick.model_prob)}`}>
                        {(pick.model_prob * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-center font-mono text-sm">
                        {formatOdds(pick.best_odds)}
                      </td>
                      <td className="px-4 py-3 text-center text-xs text-gray-500">
                        {pick.bookmaker || 'N/A'}
                      </td>
                      <td className={`px-4 py-3 text-center font-semibold ${getEdgeColor(pick.edge)}`}>
                        {pick.edge ? `+${(pick.edge * 100).toFixed(1)}%` : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="font-bold text-blue-700">{pick.bet_units?.toFixed(1)}U</div>
                        <div className="text-xs text-gray-500">${pick.bet_amount?.toFixed(0)}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {pick.stats?.pts?.toFixed(1)} / {pick.stats?.reb?.toFixed(1)} / {pick.stats?.ast?.toFixed(1)}
                        <div className="text-xs text-gray-400">
                          {isDD ? 
                            `DD: ${(pick.l20_dd_rate * 100).toFixed(0)}%` : 
                            `TD: ${(pick.l20_td_rate * 100).toFixed(0)}%`
                          }
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Table 2: All >35% Probability Players */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-3">
          📊 All Players &gt;35% DD Probability
        </h3>
        
        {!high_probability || high_probability.length === 0 ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-600">
            No players above 35% probability today
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-300 rounded-lg">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Player</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Game</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Model %</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Odds</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Book</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Implied %</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Edge</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Stats (L20)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {high_probability.map((player, idx) => (
                  <tr key={idx} className={`hover:bg-gray-50 ${player.has_positive_edge ? '' : 'opacity-60'}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {player.player}
                      {player.has_positive_edge && (
                        <span className="ml-2 text-green-600">✓</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{player.game}</td>
                    <td className={`px-4 py-3 text-center font-semibold ${getProbColor(player.model_prob)}`}>
                      {(player.model_prob * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-center font-mono text-sm">
                      {formatOdds(player.best_odds)}
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-gray-500">
                      {player.bookmaker || 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">
                      {player.implied_prob ? `${(player.implied_prob * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className={`px-4 py-3 text-center font-semibold ${getEdgeColor(player.edge)}`}>
                      {player.edge ? 
                        (player.edge > 0 ? `+${(player.edge * 100).toFixed(1)}%` : `${(player.edge * 100).toFixed(1)}%`) 
                        : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {player.stats?.pts?.toFixed(1)} / {player.stats?.reb?.toFixed(1)} / {player.stats?.ast?.toFixed(1)}
                      <div className="text-xs text-gray-400">
                        DD: {(player.l20_dd_rate * 100).toFixed(0)}% | {player.avg_minutes?.toFixed(1)} min
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-2">Legend</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-600">
          <div><strong>Model %:</strong> Model's predicted probability</div>
          <div><strong>Odds:</strong> Best available odds (American format)</div>
          <div><strong>Edge:</strong> Model % - Implied % (positive = value bet)</div>
          <div><strong>Bet:</strong> Recommended bet size (Quarter Kelly)</div>
          <div><strong>Stats:</strong> Recent averages (Points / Rebounds / Assists)</div>
          <div><strong>✓:</strong> Has positive edge (model likes the price)</div>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          <p><strong>Bankroll Management:</strong> Bets sized using Quarter Kelly with 5% max per bet.</p>
          <p><strong>Data:</strong> Model uses last 20 games of historical data through most recent completed games.</p>
        </div>
      </div>
    </div>
  );
};

export default NBADDTDPicksV2;
