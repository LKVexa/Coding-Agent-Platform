// (C) 2026 RUSSELL PHILIP SMITHSON. C#5/.NET4.8. AUTHORING ONLY.
// Pure bounded C0322 provider: no writes/process/network/model/queue operations.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Harness;

namespace D0007P2PV1 {
 public sealed class ContractError:Exception { public ContractError(string code):base(code){} }
 public static class J {
  public static Dictionary<string,object> O(params object[] kv){var d=H.O();for(int n=0;n<kv.Length;n+=2)d.Add((string)kv[n],kv[n+1]);return d;}
  public static void Need(bool condition,string code){if(!condition)throw new ContractError(code);}
  public static Dictionary<string,object> D(object x){var d=x as Dictionary<string,object>;Need(d!=null,"object_required");return d;}
  public static List<object> A(object x){Need(x is IList,"array_required");return ((IEnumerable)x).Cast<object>().ToList();}
  public static string S(Dictionary<string,object> d,string k){object x;Need(d.TryGetValue(k,out x)&&x is string&&!String.IsNullOrWhiteSpace((string)x),"string_"+k);return (string)x;}
  public static int I(Dictionary<string,object> d,string k){object x;Need(d.TryGetValue(k,out x)&&x is int,"integer_"+k);return (int)x;}
  public static void Fields(Dictionary<string,object> d,params string[] names){Need(d.Keys.OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(names.OrderBy(x=>x,StringComparer.Ordinal)),"field_set");}
  public static string Sha(object x){return H.ShaText(H.Canon(x));}
  public static Dictionary<string,object> Clone(object x){return D(H.Parse(H.Canon(x)));}
  public static List<Dictionary<string,object>> Rows(string json){return A(H.Parse(json)).Select(D).ToList();}
 }
 public sealed class Package {
  public Dictionary<string,byte[]> Artifacts;
  public Dictionary<string,object> NativeStatus;
  public Dictionary<string,object> NativeAssessment;
 }
 public sealed class PreparationBindings {
  public const string PlanSha="c41f27de7ff6cec21d8ccd94a70ea64e372a63cec0edfbd49925879a48301f9d";
  public const string PrimarySha="6b4a629a61af45f208e7cd5e4fcba60f9d5961812bcfe66178b0e767b0eb090c";
  public const string PromptsSha="c81806dd037630273b3f4722a7fcc030fe04f953a3402b2142d5961cbeb6cb13";
  public const string PrepSha="699c091ba0fcb20aa39f0f848039ab1927871023a47e633ec7a700b8f4efa196";
  readonly Dictionary<string,string> pins=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
  readonly Dictionary<string,string> prompts=new Dictionary<string,string>(StringComparer.Ordinal);
  readonly Dictionary<string,Dictionary<string,object>> definitions=new Dictionary<string,Dictionary<string,object>>(StringComparer.Ordinal);
  string specRoot;string[] specInventory;
  public string PlanText,ImplementationSource,PrimaryExcerpt;
  public Dictionary<string,object> SourcePins;
  public static void NoLinks(string path){
   for(string p=Path.GetFullPath(path);p!=null;p=Path.GetDirectoryName(p)){
    FileAttributes a;try{a=File.GetAttributes(p);}catch(FileNotFoundException){continue;}catch(DirectoryNotFoundException){continue;}
    J.Need((a&FileAttributes.ReparsePoint)==0,"reparse_input");
   }
  }
  static string[] Files(string root){
   NoLinks(root);var result=new List<string>();var pending=new Stack<string>();pending.Push(root);
   while(pending.Count>0){string dir=pending.Pop();NoLinks(dir);foreach(string p in Directory.GetFileSystemEntries(dir)){
    NoLinks(p);if((File.GetAttributes(p)&FileAttributes.Directory)!=0)pending.Push(p);else result.Add(Path.GetFullPath(p));
   }}
   return result.OrderBy(x=>x,StringComparer.Ordinal).ToArray();
  }
  string Pin(string path,string sha){NoLinks(path);byte[] bytes=File.ReadAllBytes(path);J.Need(H.Sha(bytes)==sha,"pin_mismatch:"+Path.GetFileName(path));pins.Add(Path.GetFullPath(path),sha);return H.Utf8.GetString(bytes);}
  public static PreparationBindings Load(string preparationRoot,string specificationRoot,string versionRoot){
   var b=new PreparationBindings();
   b.Pin(Path.Combine(preparationRoot,"PREPARATION.json"),PrepSha);
   var ps=J.D(H.Parse(b.Pin(Path.Combine(preparationRoot,"PROMPTS.json"),PromptsSha)));
   b.PlanText=b.Pin(Path.Combine(versionRoot,"PLAN.md"),PlanSha);
   string html=b.Pin(Path.Combine(preparationRoot,"raw-sources/frognano-2609.07925v2.html"),PrimarySha);
   var p2=Regex.Match(html,"(?s)<div id=\"S3.p2\".*?</div>");var p3=Regex.Match(html,"(?s)<div id=\"S3.p3\".*?</div>");
   J.Need(p2.Success&&p3.Success&&p2.Value.Contains("pass-to-pass (P2P)")&&p2.Value.Contains("remains stable")&&p3.Value.Contains("P2P tests guard against regressions")&&p3.Value.Contains("hidden from the solver"),"primary_definition_missing");
   b.PrimaryExcerpt=p2.Value+"\n"+p3.Value+"\n";
   b.specRoot=Path.GetFullPath(specificationRoot);b.specInventory=Files(b.specRoot);
   J.Need(b.specInventory.Length==6,"spec_inventory");
   var declaredSpecs=J.A(ps["spec_files"]).Select(J.D).ToList();
   J.Need(declaredSpecs.Count==6&&declaredSpecs.Select(r=>Path.GetFileName(J.S(r,"path"))).Distinct(StringComparer.Ordinal).Count()==6,"prepared_spec_inventory");
   foreach(string f in b.specInventory){
    string name=Path.GetFileName(f);var records=declaredSpecs.Where(r=>Path.GetFileName(J.S(r,"path"))==name).ToList();
    J.Need(records.Count==1&&Path.GetDirectoryName(f)==b.specRoot,"prepared_spec_mapping");
    b.Pin(f,J.S(records[0],"sha256"));J.Need(new FileInfo(f).Length==J.I(records[0],"bytes"),"prepared_spec_length");
   }
   var manifest=J.D(H.ParseFile(Path.Combine(b.specRoot,"manifest.json")));
   var cross=J.D(H.ParseFile(Path.Combine(b.specRoot,"UNIT-CROSSWALK.json")));
   J.Need(J.S(ps,"product")=="D0007"&&J.S(manifest,"id")=="D0007"&&J.S(manifest,"version")=="1.1.0"&&J.S(cross,"id")=="D0007","product_identity");
   var units=J.A(cross["units"]).Select(J.D).Where(x=>J.S(x,"natural_unit")=="C0322").ToList();
   J.Need(units.Count==1&&J.A(units[0]["pair_ids"]).Select(x=>(string)x).OrderBy(x=>x).SequenceEqual(Pipeline.PairIds()),"C0322_crosswalk");
   foreach(string id in Pipeline.PairIds()){
    var original=J.A(ps["pairs"]).Select(J.D).Where(x=>J.S(x,"id")==id).ToList();
    var declared=J.A(manifest["pairs"]).Select(J.D).Where(x=>J.S(x,"id")==id).ToList();
    J.Need(original.Count==1&&declared.Count==1&&J.S(declared[0],"collection")=="COMP"&&J.S(declared[0],"role")=="core","pair_manifest");
    var r=original[0];string expected=id=="C0322-01"?"93d847e8d89a28dc4dc49cda84dc91fbf8da09b5374c299a94c803e1f4f74c3c":"ccd256a383d0d3205df19c8d08cc3f68c2e561d76def52ea0f8d0dad86bf7664";
    string prompt=b.Pin(Path.Combine(preparationRoot,"prompts/"+id+".md"),expected);
    J.Need(J.S(r,"decoded_sha256")==expected&&H.Utf8.GetByteCount(prompt)==J.I(r,"decoded_bytes")&&prompt.Contains("COMPONENT ID: "+id)&&prompt.Contains("PARENT ENTRY: C0322"),"prompt_identity");
    var stages=J.A(J.D(r["native_workflow"])["stages"]).Select(J.D).ToList();
    J.Need(stages.Count==8&&stages.Select(s=>J.I(s,"number")).SequenceEqual(Enumerable.Range(1,8))&&stages.All(s=>prompt.Contains(J.S(s,"original_text"))),"native_workflow");
    J.Need(prompt.Contains("Use a diagnostic fixture when a sibling is unavailable")&&prompt.Contains("Component validation can be complete while parent-level integration remains unverified"),"fixture_scope_permission");
    b.definitions.Add(id,J.Clone(r));b.prompts.Add(id,prompt);
   }
   string source=Path.Combine(versionRoot,"src/P2PDiagnostics.cs");NoLinks(source);b.ImplementationSource=b.Pin(source,H.ShaFile(source));
   b.SourcePins=J.O("primary_sha256",PrimarySha,"primary_locator","FrogNano v2 section3 #S3.p2 and #S3.p3","plan_sha256",PlanSha,"prompts_sha256",PromptsSha,"preparation_sha256",PrepSha,
    "implementation_sha256",H.ShaText(b.ImplementationSource),"input_files",b.pins.ToDictionary(x=>x.Key,x=>(object)x.Value),
    "reuse","Fresh authored fixture only; no prior product output accepted","source_state","present and relevant P2P/F2P definition reviewed",
    "reproduction_limits","No original repository dataset, TaskPilot synthesis, model training or real parent integration");
   b.Recheck();return b;
  }
  public void Recheck(){J.Need(Files(specRoot).SequenceEqual(specInventory,StringComparer.Ordinal),"spec_inventory_changed");foreach(var p in pins){NoLinks(p.Key);J.Need(H.ShaFile(p.Key)==p.Value,"binding_changed:"+Path.GetFileName(p.Key));}}
  public Dictionary<string,object> Definition(string id){J.Need(definitions.ContainsKey(id),"unknown_pair");return J.Clone(definitions[id]);}
  public string Prompt(string id){return prompts[id];}
 }
 public sealed class CaseDef {
  public readonly string Id,Task,Version,Group,Split;public readonly int[] Arguments;
  public CaseDef(string id,string task,string version,string split,params int[] arguments){Id=id;Task=task;Version=version;Group=task;Split=split;Arguments=(int[])arguments.Clone();}
  public Dictionary<string,object> Row(){return J.O("case_id",Id,"task_id",Task,"task_version",Version,"group",Group,"split",Split,"arguments",Arguments,"origin","fresh-authored-bounded-fixture");}
 }
 // Candidate code receives numeric arguments only. It never reads evaluator labels.
 public static class Candidates {
  public static int ClampInitial(int x,int lo,int hi){if(lo>hi)throw new ArgumentException();if(x<lo)return lo;if(x>hi)return x;return x;}
  public static int ClampCorrect(int x,int lo,int hi){if(lo>hi)throw new ArgumentException();if(x<lo)return lo;if(x>hi)return hi;return x;}
  public static int ClampRegression(int x,int lo,int hi){if(lo>hi)throw new ArgumentException();if(x<lo)return lo;if(x>hi)return hi;return lo;}
  public static long MagnitudeInitial(int x){return x<0?(long)unchecked(-x):(long)x;}
  public static long MagnitudeCorrect(int x){return x<0?-(long)x:(long)x;}
  public static long MagnitudeRegression(int x){if(x==Int32.MinValue)return 2147483648L;return x<0?0L:(long)x;}
 }
 // Literal oracle values/category sets are independent of candidate algorithms.
 static class LiteralOracle {
  static readonly string[] Values={"value:0","value:3","value:5","exception:ArgumentException","value:4","value:-10","value:10","value:5",
   "value:2147483648","value:5","value:1","value:0","value:1","value:2147483647"};
  public static string Expected(string id){int i=Array.FindIndex(Pipeline.Cases(),x=>x.Id==id);J.Need(i>=0,"oracle_unknown_case");return Values[i];}
  public static string Kind(string id){return new[]{"DEV-T03","DEV-T07","FINAL-T01"}.Contains(id)?"F2P":"P2P";}
  public static List<Dictionary<string,object>> Labels(){return Pipeline.Cases().Select(c=>J.O("case_id",c.Id,"task_version",c.Version,"expected",Expected(c.Id),"declared_kind",Kind(c.Id))).ToList();}
 }
 public sealed class Experiment {
  public readonly List<Dictionary<string,object>> Observations;
  public readonly int MethodCalls;
  internal Experiment(List<Dictionary<string,object>> rows,int calls){Observations=rows;MethodCalls=calls;}
 }
 public sealed class Dataset {
  public readonly string InputsJson,OutcomesJson,LabelsJson,PassingJson,ExclusionsJson,ManifestJson;
  internal Dataset(string a,string b,string c,string d,string e,string f){InputsJson=a;OutcomesJson=b;LabelsJson=c;PassingJson=d;ExclusionsJson=e;ManifestJson=f;}
  public string ManifestSha { get {return H.ShaText(ManifestJson);} }
 }
 public static class Pipeline {
  public const string Version="d0007-p2p-bounded/1.0.0";
  public const string Label="PROMPT-VERSION-MISMATCH: original pre-v3 source used";
  static readonly string[] Variants={"initial","correct","regression"};
  public static string[] PairIds(){return new[]{"C0322-01","C0322-02"};}
  public static CaseDef[] Cases(){return new[]{
   new CaseDef("DEV-T01","DEV-CLAMP","clamp-v1","development",-2,0,5),new CaseDef("DEV-T02","DEV-CLAMP","clamp-v1","development",3,0,5),
   new CaseDef("DEV-T03","DEV-CLAMP","clamp-v1","development",9,0,5),new CaseDef("DEV-T04","DEV-CLAMP","clamp-v1","development",0,3,2),
   new CaseDef("DEV-T05","DEV-CLAMP","clamp-v1","development",4,4,4),new CaseDef("DEV-T06","DEV-CLAMP","clamp-v1","development",Int32.MinValue,-10,10),
   new CaseDef("DEV-T07","DEV-CLAMP","clamp-v1","development",Int32.MaxValue,-10,10),new CaseDef("DEV-T08","DEV-CLAMP","clamp-v1","development",5,0,5),
   new CaseDef("FINAL-T01","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",Int32.MinValue),new CaseDef("FINAL-T02","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",-5),
   new CaseDef("FINAL-T03","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",-1),new CaseDef("FINAL-T04","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",0),
   new CaseDef("FINAL-T05","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",1),new CaseDef("FINAL-T06","FINAL-MAGNITUDE","magnitude-v1","final-evaluation",Int32.MaxValue)
  };}
  public static List<Dictionary<string,object>> Inputs(){return Cases().Select(c=>c.Row()).ToList();}
  public static void CheckSplits(IEnumerable<Dictionary<string,object>> rows){
   var groups=new Dictionary<string,string>(StringComparer.Ordinal);
   foreach(var r in rows){string group=J.S(r,"group"),split=J.S(r,"split"),old;J.Need(group=="DEV-CLAMP"||group=="FINAL-MAGNITUDE","unknown_group");
    if(groups.TryGetValue(group,out old))J.Need(old==split,"group_crosses_splits");else groups.Add(group,split);
    J.Need(split==(group=="DEV-CLAMP"?"development":"final-evaluation"),"split_policy");}
  }
  public static List<Dictionary<string,object>> LoadInputs(IEnumerable<Dictionary<string,object>> rows){
   var list=rows.Select(J.Clone).ToList();CheckSplits(list);var map=Cases().ToDictionary(c=>c.Id,StringComparer.Ordinal);var seen=new HashSet<string>(StringComparer.Ordinal);
   foreach(var r in list){J.Fields(r,"case_id","task_id","task_version","group","split","arguments","origin");string id=J.S(r,"case_id");J.Need(map.ContainsKey(id)&&seen.Add(id),"duplicate_unknown_input");
    var args=J.A(r["arguments"]);J.Need(args.All(x=>x is int),"integer_arguments");J.Need(H.Canon(r)==H.Canon(map[id].Row()),"input_identity_version_or_corruption");}
   J.Need(seen.SetEquals(map.Keys),"input_inventory");return list.OrderBy(r=>J.S(r,"case_id"),StringComparer.Ordinal).ToList();
  }
  public static Experiment ExecuteAll(){
   var rows=new List<Dictionary<string,object>>();int calls=0;
   foreach(var c in Cases())foreach(string variant in Variants){
    string outcome,state="completed";calls++;
    try{
     long value;
     if(c.Task=="DEV-CLAMP"){
      if(variant=="initial")value=Candidates.ClampInitial(c.Arguments[0],c.Arguments[1],c.Arguments[2]);
      else if(variant=="correct")value=Candidates.ClampCorrect(c.Arguments[0],c.Arguments[1],c.Arguments[2]);
      else value=Candidates.ClampRegression(c.Arguments[0],c.Arguments[1],c.Arguments[2]);
     }else{
      if(variant=="initial")value=Candidates.MagnitudeInitial(c.Arguments[0]);
      else if(variant=="correct")value=Candidates.MagnitudeCorrect(c.Arguments[0]);
      else value=Candidates.MagnitudeRegression(c.Arguments[0]);
     }
     outcome="value:"+value.ToString(CultureInfo.InvariantCulture);
    }catch(ArgumentException){outcome="exception:ArgumentException";}
    catch(Exception e){state="runtime_error";outcome=e.GetType().FullName+": "+e.Message;}
    rows.Add(J.O("observation_id",c.Id+":"+variant,"case_id",c.Id,"task_id",c.Task,"task_version",c.Version,"split",c.Split,
     "variant",variant,"call_ordinal",calls,"execution_state",state,"outcome",outcome));
   }
   return new Experiment(rows,calls);
  }
  static bool ValidOutcome(string value){long n;if(value=="exception:ArgumentException")return true;if(!value.StartsWith("value:",StringComparison.Ordinal))return false;string number=value.Substring(6);
   return Regex.IsMatch(number,@"^-?(0|[1-9][0-9]*)$")&&Int64.TryParse(number,NumberStyles.AllowLeadingSign,CultureInfo.InvariantCulture,out n)&&n.ToString(CultureInfo.InvariantCulture)==number;}
  public static List<Dictionary<string,object>> LoadOutcomes(IEnumerable<Dictionary<string,object>> rows){
   var map=Cases().ToDictionary(c=>c.Id,StringComparer.Ordinal);var seen=new HashSet<string>(StringComparer.Ordinal);var ordinals=new HashSet<int>();var list=rows.Select(J.Clone).ToList();
   foreach(var r in list){J.Fields(r,"observation_id","case_id","task_id","task_version","split","variant","call_ordinal","execution_state","outcome");
    string id=J.S(r,"case_id"),variant=J.S(r,"variant");J.Need(map.ContainsKey(id)&&Variants.Contains(variant),"observation_identity");
    var c=map[id];J.Need(J.S(r,"observation_id")==id+":"+variant&&seen.Add(id+":"+variant),"duplicate_observation");
    J.Need(J.S(r,"task_id")==c.Task&&J.S(r,"task_version")==c.Version&&J.S(r,"split")==c.Split,"observation_version_split");
    int ordinal=J.I(r,"call_ordinal");J.Need(ordinal>=1&&ordinal<=42&&ordinals.Add(ordinal)&&ordinal==Array.FindIndex(Cases(),item=>item.Id==id)*3+Array.IndexOf(Variants,variant)+1,"call_ordinal");
    J.Need(J.S(r,"execution_state")=="completed"&&ValidOutcome(J.S(r,"outcome")),"invalid_execution_outcome");
   }
   J.Need(list.Count==42&&seen.Count==42&&ordinals.Count==42,"observation_inventory");
   return list.OrderBy(r=>J.S(r,"observation_id"),StringComparer.Ordinal).ToList();
  }
  public static List<Dictionary<string,object>> LoadLabels(IEnumerable<Dictionary<string,object>> labels){
   var expected=LiteralOracle.Labels().ToDictionary(r=>J.S(r,"case_id"),StringComparer.Ordinal);var seen=new HashSet<string>();var list=labels.Select(J.Clone).ToList();
   foreach(var r in list){J.Fields(r,"case_id","task_version","expected","declared_kind");string id=J.S(r,"case_id");J.Need(expected.ContainsKey(id)&&seen.Add(id),"duplicate_unknown_label");J.Need(H.Canon(r)==H.Canon(expected[id]),"label_alignment");}
   J.Need(list.Count==14,"label_inventory");return list.OrderBy(r=>J.S(r,"case_id"),StringComparer.Ordinal).ToList();
  }
  public static Dataset CreateDataset(IEnumerable<Dictionary<string,object>> input,IEnumerable<Dictionary<string,object>> observations,IEnumerable<Dictionary<string,object>> labels){
   var ins=LoadInputs(input);var obs=LoadOutcomes(observations);var ls=LoadLabels(labels);
   var passing=new List<object>();var exclusions=new List<object>();
   foreach(var c in ins){
    string id=J.S(c,"case_id");var before=obs.Single(x=>J.S(x,"case_id")==id&&J.S(x,"variant")=="initial");var label=ls.Single(x=>J.S(x,"case_id")==id);
    bool pass=J.S(before,"outcome")==J.S(label,"expected");J.Need((pass?"P2P":"F2P")==J.S(label,"declared_kind"),"initial_category_differs_from_literal_protocol");
    var row=J.O("case_id",id,"task_id",c["task_id"],"task_version",c["task_version"],"group",c["group"],"split",c["split"],
     "input_sha256",J.Sha(c),"initial_observation_sha256",J.Sha(before),"initial_outcome",before["outcome"],"expected_outcome",label["expected"],"category",pass?"P2P":"F2P");
    if(pass)passing.Add(row);else{row.Add("exclusion_reason","excluded_from_P2P_initially_failing");exclusions.Add(row);}
   }
   string a=H.Canon(ins),b=H.Canon(obs),cjson=H.Canon(ls),d=H.Canon(passing),e=H.Canon(exclusions);
   string manifest=H.Canon(J.O("schema","c0322-p2p-dataset/1","version",Version,"origin","fresh_raw_fixture_no_prior_producer_accepted","raw_inputs",J.O("count",14,"canonical_records_sha256",H.ShaText(a)),
    "raw_observations",J.O("count",42,"canonical_records_sha256",H.ShaText(b)),"private_labels",J.O("count",14,"canonical_records_sha256",H.ShaText(cjson)),
    "passing_slice",J.O("count",passing.Count,"canonical_records_sha256",H.ShaText(d)),"exclusions",J.O("count",exclusions.Count,"canonical_records_sha256",H.ShaText(e)),
    "split_groups",J.O("development","DEV-CLAMP","final-evaluation","FINAL-MAGNITUDE"),"fitting",false,"model_selection",false));
   return new Dataset(a,b,cjson,d,e,manifest);
  }
  static void VerifyDataset(Dataset d){
   var rebuilt=CreateDataset(J.Rows(d.InputsJson),J.Rows(d.OutcomesJson),J.Rows(d.LabelsJson));
   J.Need(rebuilt.ManifestJson==d.ManifestJson&&rebuilt.PassingJson==d.PassingJson&&rebuilt.ExclusionsJson==d.ExclusionsJson,"dataset_provenance_or_transformation");
  }
  public static Dictionary<string,object> Preserve(Dataset data,IEnumerable<Dictionary<string,object>> observations,string variant){
   J.Need(variant=="correct"||variant=="regression","consumer_variant");VerifyDataset(data);var obs=LoadOutcomes(observations);
   J.Need(H.Canon(obs)==data.OutcomesJson,"consumer_input_manifest_mismatch");var p2p=J.Rows(data.PassingJson);var rows=new List<object>();var regressed=new List<string>();
   foreach(var before in p2p){string id=J.S(before,"case_id");var after=obs.Single(x=>J.S(x,"case_id")==id&&J.S(x,"variant")==variant);
    bool pass=J.S(after,"outcome")==J.S(before,"initial_outcome");if(!pass)regressed.Add(id);
    rows.Add(J.O("case_id",id,"task_id",before["task_id"],"task_version",before["task_version"],"split",before["split"],
     "before",before["initial_outcome"],"after",after["outcome"],"preserved",pass,"input_sha256",before["input_sha256"],
     "before_observation_sha256",before["initial_observation_sha256"],"after_observation_sha256",J.Sha(after)));
   }
   return J.O("schema","c0322-preservation-result/1","variant",variant,"producer_mode","fresh_raw_fixture_no_prior_producer_accepted","producer_manifest_sha256",data.ManifestSha,
    "p2p_total",rows.Count,"p2p_preserved",rows.Count-regressed.Count,"regressions",regressed,"accepted",regressed.Count==0,"rows",rows,
    "downstream_status",regressed.Count==0?"accept":"reject","consumer_calls_to_candidates",0,"limits","Finite authored P2P fixture; real parent integration unverified");
  }
  public static string Downstream(Dictionary<string,object> report,string expectedManifest){
   J.Need(J.S(report,"schema")=="c0322-preservation-result/1"&&J.S(report,"producer_manifest_sha256")==expectedManifest&&report["accepted"] is bool,"downstream_report_identity");
   var rows=J.A(report["rows"]).Select(J.D).ToList();J.Need(rows.Count==11&&rows.All(x=>x["preserved"] is bool),"downstream_inventory");
   var expectedIds=new HashSet<string>(Cases().Where(c=>LiteralOracle.Kind(c.Id)=="P2P").Select(c=>c.Id),StringComparer.Ordinal);
   var seen=new HashSet<string>(StringComparer.Ordinal);
   foreach(var row in rows){
    J.Fields(row,"case_id","task_id","task_version","split","before","after","preserved","input_sha256","before_observation_sha256","after_observation_sha256");
    string id=J.S(row,"case_id");J.Need(expectedIds.Contains(id)&&seen.Add(id),"downstream_duplicate_or_unknown_case");
    var c=Cases().Single(x=>x.Id==id);
    J.Need(J.S(row,"task_id")==c.Task&&J.S(row,"task_version")==c.Version&&J.S(row,"split")==c.Split,"downstream_task_version_split");
    J.Need(ValidOutcome(J.S(row,"before"))&&ValidOutcome(J.S(row,"after"))&&(bool)row["preserved"]==(J.S(row,"before")==J.S(row,"after")),"downstream_outcome_contradiction");
    foreach(string field in new[]{"input_sha256","before_observation_sha256","after_observation_sha256"})J.Need(Regex.IsMatch(J.S(row,field),"^[0-9a-f]{64}$"),"downstream_hash_shape");
   }
   J.Need(seen.SetEquals(expectedIds),"downstream_missing_case");
   int good=rows.Count(x=>(bool)x["preserved"]);bool accepted=good==11;
   J.Need(J.I(report,"p2p_total")==11&&J.I(report,"p2p_preserved")==good&&(bool)report["accepted"]==accepted&&J.S(report,"downstream_status")==(accepted?"accept":"reject"),"downstream_contradiction");
   return accepted?"accept":"reject";
  }
  static List<object> SummaryRows(List<Dictionary<string,object>> obs){
   var rows=new List<object>();foreach(string task in new[]{"DEV-CLAMP","FINAL-MAGNITUDE"})foreach(string variant in Variants){
    var selected=obs.Where(r=>J.S(r,"task_id")==task&&J.S(r,"variant")==variant).ToList();
    var f2p=selected.Where(r=>LiteralOracle.Kind(J.S(r,"case_id"))=="F2P").ToList();var p2p=selected.Where(r=>LiteralOracle.Kind(J.S(r,"case_id"))=="P2P").ToList();
    rows.Add(J.O("task_id",task,"variant",variant,"total",selected.Count,"passed",selected.Count(r=>J.S(r,"outcome")==LiteralOracle.Expected(J.S(r,"case_id"))),
     "F2P_total",f2p.Count,"F2P_passed",f2p.Count(r=>J.S(r,"outcome")==LiteralOracle.Expected(J.S(r,"case_id"))),
     "P2P_total",p2p.Count,"P2P_passed",p2p.Count(r=>J.S(r,"outcome")==LiteralOracle.Expected(J.S(r,"case_id")))));
   }return rows;
  }
  static void Check(List<object> checks,string id,object input,object expected,object actual){
   int stage=id=="actual_method_call_count"||id.StartsWith("literal_",StringComparison.Ordinal)||id=="execution_or_dataset_contract"?4:id.Contains("handoff")||id.StartsWith("downstream_",StringComparison.Ordinal)||id=="consumer_replay_from_saved_inputs"?6:5;
   checks.Add(J.O("id",id,"stage",stage,"inputs",input,"expected",expected,"observed",actual,"result",H.Canon(expected)==H.Canon(actual)?"pass":"fail","evidence","evidence/diagnostics.json#"+id,"scope","bounded authored fixture"));
  }
  static void Reject(List<object> checks,string id,object input,Action action){
   string actual;try{action();actual="accepted";}catch(ContractError){actual="rejected";}Check(checks,id,input,"rejected",actual);
  }
  static List<Dictionary<string,object>> CloneRows(IEnumerable<Dictionary<string,object>> rows){return rows.Select(J.Clone).ToList();}
  public static List<object> Diagnostics(Dataset data,Experiment experiment){
   var checks=new List<object>();var input=Inputs();var obs=LoadOutcomes(experiment.Observations);var labels=LiteralOracle.Labels();
   Check(checks,"actual_method_call_count",J.O("cases",14,"variants",3),42,experiment.MethodCalls);
   Check(checks,"input_count",null,14,LoadInputs(input).Count);
   Check(checks,"P2P_ids_literal",null,new[]{"DEV-T01","DEV-T02","DEV-T04","DEV-T05","DEV-T06","DEV-T08","FINAL-T02","FINAL-T03","FINAL-T04","FINAL-T05","FINAL-T06"},J.Rows(data.PassingJson).Select(r=>J.S(r,"case_id")).ToArray());
   Check(checks,"F2P_exclusions_literal",null,new[]{"DEV-T03","DEV-T07","FINAL-T01"},J.Rows(data.ExclusionsJson).Select(r=>J.S(r,"case_id")).ToArray());
   var summary=SummaryRows(obs).Select(J.D).ToList();int[] totals={6,8,6,5,6,4};int[] p2p={6,6,4,5,5,3};int[] f2p={0,2,2,0,1,1};
   Check(checks,"literal_pass_totals",null,totals,summary.Select(r=>J.I(r,"passed")).ToArray());
   Check(checks,"literal_P2P_totals",null,p2p,summary.Select(r=>J.I(r,"P2P_passed")).ToArray());
   Check(checks,"literal_F2P_totals",null,f2p,summary.Select(r=>J.I(r,"F2P_passed")).ToArray());
   string rawBefore=H.Canon(input);var reversed=CreateDataset(input.AsEnumerable().Reverse(),obs.AsEnumerable().Reverse(),labels.AsEnumerable().Reverse());
   Check(checks,"order_independent_label_alignment",null,data.ManifestSha,reversed.ManifestSha);
   Check(checks,"raw_inputs_unchanged",null,rawBefore,H.Canon(input));
   var roundtrip=CreateDataset(J.Rows(data.InputsJson),J.Rows(data.OutcomesJson),J.Rows(data.LabelsJson));
   Check(checks,"dataset_serialization_replay",null,data.ManifestJson,roundtrip.ManifestJson);
   var correct=Preserve(data,obs,"correct");var regression=Preserve(data,obs,"regression");
   Check(checks,"normal_preservation_handoff",correct,"accept",Downstream(correct,data.ManifestSha));
   Check(checks,"regression_preservation_handoff",regression,"reject",Downstream(regression,data.ManifestSha));
   Check(checks,"regression_ids_literal",null,new[]{"DEV-T02","DEV-T08","FINAL-T02","FINAL-T03"},regression["regressions"]);
   Check(checks,"regression_preserved_literal",null,7,regression["p2p_preserved"]);
   bool f2pOnly=obs.Where(r=>J.S(r,"variant")=="regression"&&LiteralOracle.Kind(J.S(r,"case_id"))=="F2P").All(r=>J.S(r,"outcome")==LiteralOracle.Expected(J.S(r,"case_id")));
   Check(checks,"F2P_only_control_insufficient",J.O("full_gate",regression["accepted"],"control","checks target repairs only"),J.O("F2P_only_accept",true,"P2P_gate_accept",false),J.O("F2P_only_accept",f2pOnly,"P2P_gate_accept",regression["accepted"]));
   Check(checks,"consumer_replay_from_saved_inputs",null,H.Canon(regression),H.Canon(Preserve(roundtrip,J.Rows(data.OutcomesJson),"regression")));
   foreach(string mutation in new[]{"missing_field","extra_field","wrong_version","numeric_string","duplicate","missing","unknown","cross_split"}){
    var bad=CloneRows(input);
    if(mutation=="missing_field")bad[0].Remove("origin");else if(mutation=="extra_field")bad[0]["hidden_label"]="x";
    else if(mutation=="wrong_version")bad[0]["task_version"]="v2";else if(mutation=="numeric_string")bad[0]["arguments"]=new object[]{"-2",0,5};
    else if(mutation=="duplicate")bad.Add(J.Clone(bad[0]));else if(mutation=="missing")bad.RemoveAt(0);
    else if(mutation=="unknown")bad[0]["case_id"]="OTHER";else bad[0]["split"]="final-evaluation";
    Reject(checks,"loader_reject_"+mutation,J.O("mutation",mutation),()=>LoadInputs(bad));
   }
   foreach(string mutation in new[]{"duplicate","missing","corrupt","runtime_error","wrong_version","wrong_task","wrong_ordinal"}){
    var bad=CloneRows(obs);
    if(mutation=="duplicate")bad.Add(J.Clone(bad[0]));else if(mutation=="missing")bad.RemoveAt(0);else if(mutation=="corrupt")bad[0]["outcome"]="value:NaN";
    else if(mutation=="runtime_error")bad[0]["execution_state"]="runtime_error";else if(mutation=="wrong_version")bad[0]["task_version"]="v2";else if(mutation=="wrong_task")bad[0]["task_id"]="OTHER";else bad[0]["call_ordinal"]=42;
    Reject(checks,"outcome_reject_"+mutation,J.O("mutation",mutation),()=>Preserve(data,bad,"correct"));
   }
   var dupLabel=CloneRows(labels);dupLabel.Add(J.Clone(dupLabel[0]));Reject(checks,"duplicate_label",null,()=>LoadLabels(dupLabel));
   var swapped=CloneRows(labels);object tmp=swapped[0]["expected"];swapped[0]["expected"]=swapped[1]["expected"];swapped[1]["expected"]=tmp;Reject(checks,"swapped_label",null,()=>LoadLabels(swapped));
   var badReport=J.Clone(regression);badReport["accepted"]=true;Reject(checks,"downstream_reject_contradictory_accept",null,()=>Downstream(badReport,data.ManifestSha));
   Reject(checks,"downstream_reject_wrong_manifest",null,()=>Downstream(correct,new string('0',64)));
   var repeated=J.Clone(correct);var repeatedRows=J.A(repeated["rows"]);repeatedRows[1]=J.Clone(repeatedRows[0]);repeated["rows"]=repeatedRows;
   Reject(checks,"downstream_reject_duplicate_case",null,()=>Downstream(repeated,data.ManifestSha));
   var fabricated=J.Clone(correct);var fabricatedRows=J.A(fabricated["rows"]);J.D(fabricatedRows[0])["after"]="value:999";fabricated["rows"]=fabricatedRows;
   Reject(checks,"downstream_reject_wrong_preservation_flag",null,()=>Downstream(fabricated,data.ManifestSha));
   var corruptDataset=new Dataset(data.InputsJson,data.OutcomesJson,data.LabelsJson,data.PassingJson+" ",data.ExclusionsJson,data.ManifestJson);
   Reject(checks,"processed_provenance_corruption",null,()=>Preserve(corruptDataset,obs,"correct"));
   return checks;
  }
  static void Artifact(Dictionary<string,byte[]> a,string name,object value){a.Add(name,H.Utf8.GetBytes(H.ToJson(value,false)));}
  static void Text(Dictionary<string,byte[]> a,string name,string value){a.Add(name,H.Utf8.GetBytes(value));}
  public static Package Build(string pair,PreparationBindings bindings){
   J.Need(PairIds().Contains(pair),"unknown_pair");bindings.Recheck();var definition=bindings.Definition(pair);
   var artifacts=new Dictionary<string,byte[]>(StringComparer.Ordinal);var checks=new List<object>();var experiment=ExecuteAll();Dataset dataset=null;
   Artifact(artifacts,"data/raw-inputs.json",Inputs());Artifact(artifacts,"data/raw-outcomes.json",experiment.Observations);
   Artifact(artifacts,"private-evaluator/labels.json",LiteralOracle.Labels());string error=null;
   try{
    dataset=CreateDataset(Inputs(),experiment.Observations,LiteralOracle.Labels());checks=Diagnostics(dataset,experiment);
    Text(artifacts,"data/processed-passing.json",dataset.PassingJson);Text(artifacts,"data/exclusions.json",dataset.ExclusionsJson);Text(artifacts,"data/MANIFEST.json",dataset.ManifestJson);
    Artifact(artifacts,"evidence/totals.json",SummaryRows(LoadOutcomes(experiment.Observations)));
    Artifact(artifacts,"operation/correct-trace.json",Preserve(dataset,experiment.Observations,"correct"));
    Artifact(artifacts,"operation/regression-trace.json",Preserve(dataset,experiment.Observations,"regression"));
    Artifact(artifacts,"operation/CONTRACT.json",J.O("producer","fresh authored P2P dataset producer","consumer","C0322 bounded preservation operation","downstream","typed acceptance gate",
     "producer_mode","fresh_raw_fixture_no_prior_producer_accepted","producer_manifest_sha256",dataset.ManifestSha,"accepted_prior_product_outputs",new object[0],
     "input","validated P2P rows plus complete42-outcome table; exact task/version/split/manifest identities","output","explicit accepted boolean, accept/reject status, before/after rows and regression IDs",
     "invalid_policy","refuse missing/duplicate/invalid outcomes before acceptance","parent_integration","unverified","candidate_calls_during_consumer",0));
   }catch(ContractError e){error=e.Message;Check(checks,"execution_or_dataset_contract",null,"valid",error);}
   bool passed=error==null&&checks.Count>0&&checks.All(c=>J.S(J.D(c),"result")=="pass");
   int last=passed?8:checks.Where(c=>J.S(J.D(c),"result")=="fail").Select(c=>J.I(J.D(c),"stage")).DefaultIfEmpty(4).Min()-1;
   var stageEvidence=new[]{"source/SOURCE-NOTES.md","SPEC.md","private-evaluator/labels.json","data/raw-outcomes.json","evidence/diagnostics.json","operation/CONTRACT.json","RESULTS.md","HANDOFF.md"};
   var stages=new List<object>();
   foreach(var stage in J.A(J.D(definition["native_workflow"])["stages"]).Select(J.D)){
    int n=J.I(stage,"number");stages.Add(J.O("stage",n,"original_criterion",stage["advance_when"],"original_stage_text",stage["original_text"],
     "id","native-stage-"+n.ToString(CultureInfo.InvariantCulture),"scope","component","required",true,
     "source_locator","source/ORIGINAL-CONTRACT.json native_workflow.stages["+ (n-1).ToString(CultureInfo.InvariantCulture)+"]",
     "result",n<=last?"pass":n==last+1?"fail":"unverified","evidence",n<=last?new[]{stageEvidence[n-1]}:new[]{"RESULTS.md","evidence/diagnostics.json"},
     "interpretation_limits","Bounded authored fixture component only; no original model/repository integration claim"));
   }
   Artifact(artifacts,"evidence/diagnostics.json",checks);Artifact(artifacts,"evidence/criteria-assessment.json",J.O("pair",pair,"stages",stages,"candidate_native_complete",passed,
    "mechanical_writer_qualification_required",true,"scope","Native component criteria separate from parent/product acceptance"));
   Artifact(artifacts,"source/BINDINGS.json",bindings.SourcePins);Artifact(artifacts,"source/ORIGINAL-CONTRACT.json",definition);
   Text(artifacts,"source/ORIGINAL-PROMPT.md",bindings.Prompt(pair));Text(artifacts,"source/PRIMARY-EXCERPT.html",bindings.PrimaryExcerpt);
   Text(artifacts,"source/PLAN.md",bindings.PlanText);Text(artifacts,"source/P2PDiagnostics.cs",bindings.ImplementationSource);
   Text(artifacts,"source/SOURCE-NOTES.md","# Source/evidence map\n\nFrogNano v2 section3 #S3.p2 defines original-failing/gold-passing F2P while existing P2P stays stable. #S3.p3 says F2P repairs target behavior, P2P guards regressions, and gold/generatedF2P information is hidden from the solver. PrimarySHA "+PreparationBindings.PrimarySha+".\n\nProposal: two authored task groups,14literal cases,three fixed implementations,typed loader and preservation consumer. These are not original repository/model data. Observation: see42 actual compiled-helper call records and diagnostics. No prior product output is accepted. Method-interface separation is tested; OS-level solver isolation is not claimed.\n");
   Text(artifacts,"SPEC.md","# "+pair+" bounded P2P specification\n\n"+Label+"\n\nOriginal work type: "+J.S(definition,"work_type")+"\nOriginal completion criterion: "+J.S(definition,"component_completion_criterion")+"\n\nSee source/PLAN.md for the fixed14cases,42calls, exact schemas, source-supported definitions, all proposed decisions and unchanged acceptance criteria. Source/ORIGINAL-CONTRACT.json retains every original required-work and native stage clause. The component artifact is the validated dataset/loader for01 and preservation operation for02. Candidate methods receive only integers; evaluator labels and F2P exclusions are separately retained. No fitting/model selection. DEV-CLAMP and FINAL-MAGNITUDE groups cannot cross splits. All prior output dependencies are absent; fresh raw fixture substitution is explicit.\n");
   int failures=checks.Count(x=>J.S(J.D(x),"result")=="fail");
   Text(artifacts,"VALIDATION.md","# Actual bounded validation\n\nHelper method calls: "+experiment.MethodCalls.ToString(CultureInfo.InvariantCulture)+". Diagnostic checks: "+checks.Count.ToString(CultureInfo.InvariantCulture)+", failed: "+failures.ToString(CultureInfo.InvariantCulture)+". Raw calls are in data/raw-outcomes.json; diagnostics retain expected/observed values, including rejection paths. Literal expectations come from private-evaluator/labels.json, not candidate computations. Consumer replay adds zero candidate calls. Expected wrong candidate outputs remain visible functional failures; diagnostics may pass when those failures exactly match the frozen protocol. Unexpected runtime errors cannot qualify as intended wrong answers.\n");
   Text(artifacts,"RESULTS.md","# Supported result\n\nBounded component criterion result: "+(passed?"pass":"fail")+". Last supported stage: "+last.ToString(CultureInfo.InvariantCulture)+"/8.\n\n"+(error==null?"Inspect evidence/totals.json and the correct/regression operation traces for actual finite results.":"Recorded execution/contract error: "+error)+
    "\n\nOriginal repository benchmark, TaskPilot generation, model/RL training, statistical generalization and real parent integration are unverified. F2P-only acceptance of an authored regression is an intentional insufficient control, not approval by the combined gate. No selection was fitted to either split. Source statements, implementation proposals and actual observations remain separate.\n");
   Text(artifacts,"HANDOFF.md","# Reproduction and bounded handoff\n\nUse reviewed C#5 source and frozen HarnessCommon. Load PreparationBindings with pinned D0007 preparation, six-file audited spec and this version root; call Pipeline.Build(\""+pair+"\",bindings). Each Build actually invokes42helper calls, so a replay is another42calls; the consumer-only serialized replay uses zero. Root's qualified writer must verify active ownership/preflight, source/spec/tool/policy fingerprints, schema, immutable files and A1-A6 before accepting this candidate package. Native completion is limited to the declared fixture artifact. Integration status fixture_tested means the bounded producer/consumer/gate trace only; real parent integration remains unverified.\n\nPair02 uses a fresh raw fixture, never a claimed COMPLETE01 or D5 partial output. No dependency can be inferred from source-list order. Reuse/restart only after current fingerprints and outputs match; preserve failures and at most3repair attempts. Exact original workflow and criteria are retained in source/ORIGINAL-CONTRACT.json and evidence/criteria-assessment.json. No product release or delivery is produced by this provider.\n");
   var statusChecks=checks.Select(x=>{var r=J.D(x);return (object)J.O("name",r["id"],"result",r["result"],"evidence","evidence/diagnostics.json#"+J.S(r,"id"),"iterations",1);}).ToList();
   var native=J.O("schema","catalog-status/3.0","collection","COMP","id",pair,"prompt_version","3.0.0","status",passed?"complete":"failed",
    "stage",J.O("last_completed",last,"total",8,"label",passed?"Bounded component packaged; writer verification required":"Earliest failing bounded criterion"),
    "checks",statusChecks,"updated",H.Now(),"integration_status",passed?"fixture_tested":"blocked","parent_integration_status","unverified",
    "inputs",new List<object>{J.O("name","FrogNano v2 primary source","state","present","sha256",PreparationBindings.PrimarySha),
     J.O("name","Frozen authored fixture protocol","state","present","sha256",PreparationBindings.PlanSha)},
    "scope","Bounded authored P2P data/preservation artifact; original repository/model reproduction outside this scope","source_label",Label,
    "accepted_upstream_artifacts",new object[0],"producer_mode","fresh_raw_fixture_no_prior_producer_accepted","method_calls",experiment.MethodCalls,
    "criteria_assessment","evidence/criteria-assessment.json","mechanical_writer_qualification_required",true);
   var criteria=new List<object>(stages);criteria.Add(J.O("id","real-parent-integration","stage",6,"scope","parent","required",true,"result","unverified",
    "evidence",new[]{"RESULTS.md","operation/CONTRACT.json"},"source_locator","source/ORIGINAL-PROMPT.md Integration Contract; original permits component completion separately",
    "reason","Only the explicitly declared fresh-fixture producer/consumer trace is exercised; original repository/TaskPilot integration remains unverified"));
   if(dataset==null)J.D(criteria[criteria.Count-1])["evidence"]=new[]{"RESULTS.md","evidence/diagnostics.json"};
   var assessment=J.O("schema","native-criteria-assessment/1","protocol_sha256",PreparationBindings.PlanSha,"id",pair,"collection","COMP",
    "status",native["status"],"stage",native["stage"],"criteria",criteria,"source_pins",bindings.SourcePins,
    "scope","Bounded fixture component; required parent integration remains separately unverified","accepted_upstream_artifacts",new object[0]);
   Artifact(artifacts,"evidence/NATIVE-ASSESSMENT.json",assessment);
   var fileMap=artifacts.Where(x=>x.Key.StartsWith("data/",StringComparison.Ordinal)||x.Key.StartsWith("private-evaluator/",StringComparison.Ordinal))
    .OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>(object)J.O("path",x.Key,"bytes",x.Value.Length,"sha256",H.Sha(x.Value))).ToList();
   Artifact(artifacts,"data/ARTIFACT-MANIFEST.json",J.O("schema","c0322-data-file-manifest/1","files",fileMap,
    "digest_contract","These are actual artifact-byte hashes; data/MANIFEST.json separately binds canonical record collections. The manifest itself is excluded."));
   bindings.Recheck();return new Package{Artifacts=artifacts,NativeStatus=native,NativeAssessment=assessment};
  }
 }
}
