// HarnessCommon.cs - C# 5 / .NET 4.8 harness core (JSON, hashing, atomic contained writes,
// catalog-status/3.0 subset schema validator). Ported incrementally from the earlier Python
// harness design; this is new C# code, not a wrapper around Python.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

namespace Harness
{
    public static class H
    {
        public const string HarnessVersion = "harness-cs/0.2.0";
        public static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        public static string Sha(byte[] b) { using (var s = SHA256.Create()) return BitConverter.ToString(s.ComputeHash(b)).Replace("-", "").ToLowerInvariant(); }
        public static string ShaFile(string p) { using (var s = SHA256.Create()) using (var f = File.OpenRead(p)) return BitConverter.ToString(s.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
        public static string ShaText(string t) { return Sha(Utf8.GetBytes(t)); }

        public static object Parse(string text) { var js = new JavaScriptSerializer(); js.MaxJsonLength = int.MaxValue; js.RecursionLimit = 1000; return js.DeserializeObject(text); }
        public static object ParseFile(string p) { return Parse(File.ReadAllText(p, Encoding.UTF8)); }

        public static Dictionary<string, object> O() { return new Dictionary<string, object>(); }
        public static List<object> L() { return new List<object>(); }

        public static string Str(string s)
        {
            if (s == null) return "null";
            var sb = new StringBuilder("\"");
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    default: if (c < 0x20) sb.Append("\\u" + ((int)c).ToString("x4")); else sb.Append(c); break;
                }
            }
            return sb.Append('"').ToString();
        }

        static string Num(object v)
        {
            if (v is double) { double d = (double)v; if (double.IsNaN(d) || double.IsInfinity(d)) throw new Exception("non-finite number"); return d.ToString("R", CultureInfo.InvariantCulture); }
            if (v is float) return ((double)(float)v).ToString("R", CultureInfo.InvariantCulture);
            if (v is decimal) return ((decimal)v).ToString(CultureInfo.InvariantCulture);
            return Convert.ToString(v, CultureInfo.InvariantCulture);
        }

        // Pretty JSON (2-space indent, LF). sortKeys=true gives canonical key order.
        public static string ToJson(object v, bool sortKeys) { var sb = new StringBuilder(); W(sb, v, 0, sortKeys, true); sb.Append('\n'); return sb.ToString(); }
        // Compact canonical JSON (sorted keys, "," ":" separators) for digests.
        public static string Canon(object v) { var sb = new StringBuilder(); W(sb, v, 0, true, false); return sb.ToString(); }

        static void W(StringBuilder sb, object v, int ind, bool sort, bool pretty)
        {
            string nl = pretty ? "\n" : "", sp = pretty ? " " : "";
            if (v == null) { sb.Append("null"); return; }
            if (v is string) { sb.Append(Str((string)v)); return; }
            if (v is bool) { sb.Append((bool)v ? "true" : "false"); return; }
            if (v is int || v is long || v is double || v is decimal || v is float || v is short || v is uint || v is ulong) { sb.Append(Num(v)); return; }
            var dict = v as IDictionary<string, object>;
            if (dict != null)
            {
                if (dict.Count == 0) { sb.Append("{}"); return; }
                var keys = sort ? dict.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList() : dict.Keys.ToList();
                sb.Append("{" + nl);
                for (int i = 0; i < keys.Count; i++)
                {
                    if (pretty) sb.Append(' ', (ind + 1) * 2);
                    sb.Append(Str(keys[i])).Append(":" + sp);
                    W(sb, dict[keys[i]], ind + 1, sort, pretty);
                    if (i < keys.Count - 1) sb.Append(",");
                    sb.Append(nl);
                }
                if (pretty) sb.Append(' ', ind * 2);
                sb.Append("}"); return;
            }
            var en = v as IEnumerable;
            if (en != null)
            {
                var items = en.Cast<object>().ToList();
                if (items.Count == 0) { sb.Append("[]"); return; }
                sb.Append("[" + nl);
                for (int i = 0; i < items.Count; i++)
                {
                    if (pretty) sb.Append(' ', (ind + 1) * 2);
                    W(sb, items[i], ind + 1, sort, pretty);
                    if (i < items.Count - 1) sb.Append(",");
                    sb.Append(nl);
                }
                if (pretty) sb.Append(' ', ind * 2);
                sb.Append("]"); return;
            }
            throw new Exception("unsupported JSON value type " + v.GetType());
        }

        public static string Now() { return DateTimeOffset.Now.ToString("yyyy-MM-dd'T'HH:mm:sszzz", CultureInfo.InvariantCulture); }

        // Containment: full path must be inside root; reject ADS, reserved names, traversal.
        static readonly Regex Reserved = new Regex("^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\\..*)?$", RegexOptions.IgnoreCase);
        public static string Inside(string root, string rel)
        {
            if (rel.IndexOf(':') >= 0 || Path.IsPathRooted(rel)) throw new Exception("absolute/ADS path rejected: " + rel);
            foreach (var seg in rel.Split('/', '\\')) { if (seg == ".." ) throw new Exception("traversal rejected: " + rel); if (Reserved.IsMatch(seg)) throw new Exception("reserved name rejected: " + rel); }
            string r = Path.GetFullPath(root).TrimEnd('\\') + "\\";
            string f = Path.GetFullPath(Path.Combine(root, rel));
            if (!f.StartsWith(r, StringComparison.OrdinalIgnoreCase)) throw new Exception("escapes root: " + rel);
            return f;
        }

        public static void WriteAtomic(string root, string rel, byte[] data, bool allowOverwrite)
        {
            if (data.Length == 0) throw new Exception("refusing empty file " + rel);
            string f = Inside(root, rel);
            Directory.CreateDirectory(Path.GetDirectoryName(f));
            if (File.Exists(f))
            {
                if (!allowOverwrite) throw new Exception("refusing overwrite " + rel);
                if ((File.GetAttributes(f) & FileAttributes.ReparsePoint) != 0) throw new Exception("reparse target " + rel);
            }
            if (File.Exists(f))
            {
                string backup = Inside(root, "backups/atomic/" + DateTime.Now.ToString("yyyyMMddTHHmmssfff") + "-" + Guid.NewGuid().ToString("N") + "/" + rel);
                Directory.CreateDirectory(Path.GetDirectoryName(backup)); File.Copy(f, backup, false);
                if (ShaFile(f) != ShaFile(backup)) throw new Exception("backup verification failed " + rel);
            }
            string tmp = f + ".tmp-" + Guid.NewGuid().ToString("N");
            using (var stream = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { stream.Write(data, 0, data.Length); stream.Flush(true); }
            if (File.Exists(f)) File.Replace(tmp, f, null); else File.Move(tmp, f);
            byte[] back = File.ReadAllBytes(f);
            if (Sha(back) != Sha(data)) throw new Exception("post-write verification failed " + rel);
        }
        public static void WriteText(string root, string rel, string text, bool allowOverwrite) { WriteAtomic(root, rel, Utf8.GetBytes(text), allowOverwrite); }
        public static void WriteJson(string root, string rel, object v, bool allowOverwrite) { WriteText(root, rel, ToJson(v, false), allowOverwrite); }

        public static object Get(object o, params string[] path)
        {
            foreach (var k in path) { var d = o as IDictionary<string, object>; if (d == null || !d.ContainsKey(k)) return null; o = d[k]; }
            return o;
        }
    }

    // Validator for the JSON-schema subset used by catalog-status/3.0:
    // type, required, properties, additionalProperties(bool|schema), enum, const, pattern,
    // minLength, minimum, maximum, items, format(date-time).
    public static class SchemaV
    {
        static readonly Regex DateTime = new Regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$");
        public static List<string> Validate(object schema, object inst) { var e = new List<string>(); V(schema as IDictionary<string, object>, inst, "$", e); return e; }

        static bool IsInt(object x) { return x is int || x is long || (x is decimal && decimal.Truncate((decimal)x) == (decimal)x); }
        static bool IsNum(object x) { return x is int || x is long || x is decimal || x is double; }
        static bool TypeOk(string t, object x)
        {
            switch (t)
            {
                case "object": return x is IDictionary<string, object>;
                case "array": return x is object[] || (x is IList && !(x is string));
                case "string": return x is string;
                case "integer": return IsInt(x);
                case "number": return IsNum(x);
                case "boolean": return x is bool;
                case "null": return x == null;
            }
            throw new Exception("unknown type " + t);
        }
        static bool Eq(object a, object b)
        {
            if (a == null || b == null) return a == b;
            if (IsNum(a) && IsNum(b)) return Convert.ToDecimal(a) == Convert.ToDecimal(b);
            return a.Equals(b);
        }

        static void V(IDictionary<string, object> s, object x, string at, List<string> e)
        {
            if (s == null) return;
            foreach (var k in s.Keys)
                if (!new[] { "$schema", "$id", "title", "description", "type", "required", "properties", "additionalProperties", "enum", "const", "pattern", "minLength", "minimum", "maximum", "items", "format" }.Contains(k))
                    throw new Exception("schema keyword not supported by subset validator: " + k + " at " + at);
            if (s.ContainsKey("type"))
            {
                var t = s["type"]; bool ok;
                if (t is string) ok = TypeOk((string)t, x); else ok = ((IEnumerable)t).Cast<object>().Any(tt => TypeOk((string)tt, x));
                if (!ok) { e.Add(at + ": type"); return; }
            }
            if (s.ContainsKey("const") && !Eq(s["const"], x)) e.Add(at + ": const");
            if (s.ContainsKey("enum") && !((IEnumerable)s["enum"]).Cast<object>().Any(v => Eq(v, x))) e.Add(at + ": enum (" + x + ")");
            var str = x as string;
            if (str != null)
            {
                if (s.ContainsKey("minLength") && str.Length < Convert.ToInt32(s["minLength"])) e.Add(at + ": minLength");
                if (s.ContainsKey("pattern") && !Regex.IsMatch(str, (string)s["pattern"])) e.Add(at + ": pattern");
                if (s.ContainsKey("format") && (string)s["format"] == "date-time" && !DateTime.IsMatch(str)) e.Add(at + ": format date-time");
            }
            if (IsNum(x))
            {
                if (s.ContainsKey("minimum") && Convert.ToDecimal(x) < Convert.ToDecimal(s["minimum"])) e.Add(at + ": minimum");
                if (s.ContainsKey("maximum") && Convert.ToDecimal(x) > Convert.ToDecimal(s["maximum"])) e.Add(at + ": maximum");
            }
            var d = x as IDictionary<string, object>;
            if (d != null)
            {
                if (s.ContainsKey("required")) foreach (var r in ((IEnumerable)s["required"]).Cast<object>()) if (!d.ContainsKey((string)r)) e.Add(at + ": required " + r);
                var props = s.ContainsKey("properties") ? (IDictionary<string, object>)s["properties"] : new Dictionary<string, object>();
                foreach (var kv in d)
                {
                    if (props.ContainsKey(kv.Key)) V(props[kv.Key] as IDictionary<string, object>, kv.Value, at + "." + kv.Key, e);
                    else if (s.ContainsKey("additionalProperties"))
                    {
                        var ap = s["additionalProperties"];
                        if (ap is bool) { if (!(bool)ap) e.Add(at + ": additional property " + kv.Key); }
                        else V(ap as IDictionary<string, object>, kv.Value, at + "." + kv.Key, e);
                    }
                }
            }
            if (x is IList && !(x is string) && s.ContainsKey("items"))
            {
                int i = 0; foreach (var it in (IList)x) { V(s["items"] as IDictionary<string, object>, it, at + "[" + i + "]", e); i++; }
            }
        }
    }
}