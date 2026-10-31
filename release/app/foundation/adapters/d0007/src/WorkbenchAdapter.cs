// Additive local adapter. Frozen D0007 algorithms remain byte-for-byte unchanged.
// This entry point uses only bounded in-memory fixtures and stdout/stderr.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Harness;
using D0007P2PV1;

public static class WorkbenchAdapter
{
    const string AdapterVersion = "0.1.0";
    static string GetArgument(string[] args, string key, string fallback)
    {
        int index = Array.IndexOf(args, key);
        return index < 0 ? fallback : args[index + 1];
    }
    static List<object> Totals(List<Dictionary<string, object>> observations)
    {
        var result = new List<object>();
        foreach (string task in new[] { "DEV-CLAMP", "FINAL-MAGNITUDE" })
        foreach (string variant in new[] { "initial", "correct", "regression" })
        {
            var rows = observations.Where(r => J.S(r, "task_id") == task && J.S(r, "variant") == variant).ToList();
            var f2p = rows.Where(r => LiteralOracle.Kind(J.S(r, "case_id")) == "F2P").ToList();
            var p2p = rows.Where(r => LiteralOracle.Kind(J.S(r, "case_id")) == "P2P").ToList();
            result.Add(J.O("task_id", task, "variant", variant, "total", rows.Count,
                "passed", rows.Count(r => J.S(r, "outcome") == LiteralOracle.Expected(J.S(r, "case_id"))),
                "F2P_total", f2p.Count, "F2P_passed", f2p.Count(r => J.S(r, "outcome") == LiteralOracle.Expected(J.S(r, "case_id"))),
                "P2P_total", p2p.Count, "P2P_passed", p2p.Count(r => J.S(r, "outcome") == LiteralOracle.Expected(J.S(r, "case_id")))));
        }
        return result;
    }
    public static int Main(string[] args)
    {
        try
        {
            if (args.Length != 2 && args.Length != 4) throw new ArgumentException("usage: WorkbenchD7.exe --component D0007/C0322-01|D0007/C0322-02 [--case all|initial|correct|regression]");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            for (int i = 0; i < args.Length; i += 2)
                if ((args[i] != "--component" && args[i] != "--case") || !seen.Add(args[i])) throw new ArgumentException("invalid or duplicate argument");
            string component = GetArgument(args, "--component", "");
            string selectedCase = GetArgument(args, "--case", "all");
            if (component != "D0007/C0322-01" && component != "D0007/C0322-02") throw new ArgumentException("unsupported component");
            if (!new[] { "all", "initial", "correct", "regression" }.Contains(selectedCase)) throw new ArgumentException("unsupported case");
            var experiment = Pipeline.ExecuteAll();
            var data = Pipeline.CreateDataset(Pipeline.Inputs(), experiment.Observations, LiteralOracle.Labels());
            var diagnostics = Pipeline.Diagnostics(data, experiment);
            var correct = Pipeline.Preserve(data, experiment.Observations, "correct");
            var regression = Pipeline.Preserve(data, experiment.Observations, "regression");
            var checks = diagnostics.Select(value => {
                var d = J.D(value);
                return (object)J.O("id", d["id"], "status", d["result"], "expected", d["expected"], "actual", d["observed"]);
            }).ToList();
            var totals = Totals(experiment.Observations);
            var selectedTotals = totals.Select(J.D).Where(r => selectedCase == "all" || J.S(r, "variant") == selectedCase).ToList();
            object selectedAcceptance = null;
            if (selectedCase != "all")
                selectedAcceptance = selectedTotals.All(r => J.I(r, "passed") == J.I(r, "total"));
            bool ok = checks.Select(J.D).All(d => J.S(d, "status") == "pass");
            var result = J.O(
                "schema_version", "1.0.0", "adapter_id", "d0007-p2p", "adapter_version", AdapterVersion,
                "component_id", component, "scope", "authored_fixture", "execution", ok ? "pass" : "fail",
                "scientific_validation", "unverified", "parent_integration", "unverified",
                "case", selectedCase, "candidate_accepted", selectedAcceptance, "checks", checks,
                "metrics", J.O("method_calls", experiment.MethodCalls, "input_count", 14,
                    "correct_p2p_preserved", correct["p2p_preserved"], "regression_p2p_preserved", regression["p2p_preserved"],
                    "p2p_total", regression["p2p_total"], "regression_candidate_accepted", regression["accepted"],
                    "totals", selectedTotals),
                "records", J.O("inputs", Pipeline.Inputs(), "observations", experiment.Observations,
                    "diagnostics", diagnostics, "correct", correct, "regression", regression, "totals", totals),
                "provenance", J.O("upstream_provider_version", Pipeline.Version, "upstream_harness_version", H.HarnessVersion,
                    "source_label", Pipeline.Label, "dataset_manifest_sha256", data.ManifestSha),
                "limitations", new[] { "Finite authored fixtures only; no repository benchmark, model call or training.",
                    "No original writer or PreparationBindings execution; this adapter invokes the frozen diagnostic functions directly.",
                    "Literal fixture expectations share the process; no general untrusted-code or secret-evaluator isolation is claimed." });
            Console.Out.Write(H.ToJson(result, true));
            return ok ? 0 : 1;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("REFUSED " + ex.GetType().Name + ": " + ex.Message);
            return 2;
        }
    }
}
