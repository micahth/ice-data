"""Generate a portable Tableau workbook with an embedded, aggregate CSV source."""
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "analysis/results/arrest_rate_panel.csv"


def element(parent, tag, **attributes):
    return ET.SubElement(parent, tag, {key.replace("_", "-"): value for key, value in attributes.items()})


def workbook_xml():
    root = ET.Element("workbook", {"version": "18.1", "source-platform": "win",
                                   "xmlns:user": "http://www.tableausoftware.com/xml/user"})
    source = element(element(root, "datasources"), "datasource", caption="ICE annual state panel",
                     inline="true", name="ice", version="18.1")
    connection = element(source, "connection", **{"class": "textscan"},
                         directory="data", filename="arrest_rate_panel.csv", password="", server="")
    relation = element(connection, "relation", name="arrest_rate_panel.csv",
                       table="[arrest_rate_panel#csv]", type="table")
    columns = element(relation, "columns", character_set="UTF-8", header="yes",
                      locale="en_US", separator=",")
    fields = [("state", "string"), ("year", "integer"), ("era", "string"),
              ("region", "string"), ("arrests", "integer"), ("arr_rate", "real"),
              ("d_arr_rate", "real")]
    for ordinal, (name, datatype) in enumerate(fields):
        element(columns, "column", datatype=datatype, name=name, ordinal=str(ordinal))
        dimension = name in ("state", "year", "era", "region")
        attrs = {"datatype": datatype, "name": f"[{name}]",
                 "role": "dimension" if dimension else "measure",
                 "type": "nominal" if dimension else "quantitative"}
        if name == "state":
            attrs["semantic-role"] = "[State].[Name]"
        element(source, "column", **attrs)
    sheets = element(root, "worksheets")
    for title, measure in (("Annual arrests per 100k", "arr_rate"),
                           ("Annual arrest records", "arrests")):
        sheet = element(sheets, "worksheet", name=title)
        layout = element(element(sheet, "layout-options"), "title")
        text = element(layout, "formatted-text")
        element(text, "run").text = (
            f"{title} - select one year and region; records, not people. "
            "Apprehension location is not residence or workplace.")
        table = element(sheet, "table")
        view = element(table, "view")
        element(element(view, "datasources"), "datasource", caption="ICE annual state panel", name="ice")
        dependencies = element(view, "datasource-dependencies", datasource="ice")
        for field in ("state", "year", "region", measure):
            datatype = dict(fields)[field]
            dimension = field != measure
            element(dependencies, "column", datatype=datatype, name=f"[{field}]",
                    role="dimension" if dimension else "measure",
                    type="nominal" if dimension else "quantitative")
            element(dependencies, "column-instance", column=f"[{field}]",
                    derivation="None" if dimension else "Sum",
                    name=f"[{'none' if dimension else 'sum'}:{field}:{'nk' if dimension else 'qk'}]",
                    pivot="key", type="nominal" if dimension else "quantitative")
        year_filter = element(view, "filter", **{"class": "categorical"},
                              column="[ice].[none:year:nk]")
        element(year_filter, "groupfilter", **{"function": "member"},
                level="[none:year:nk]", member="2025")
        element(view, "aggregation", value="true")
        panes = element(table, "panes")
        pane = element(panes, "pane", selection_relaxation_option="selection-relaxation-allow")
        element(pane, "view", breakdown="auto")
        element(pane, "mark", **{"class": "Bar"})
        encodings = element(pane, "encodings")
        element(encodings, "color", column="[ice].[none:region:nk]")
        element(table, "rows").text = "[ice].[none:state:nk]"
        element(table, "cols").text = f"[ice].[sum:{measure}:qk]"
    windows = element(root, "windows", saved_dpi_scale_factor="1.0", source_height="900")
    for title in ("Annual arrests per 100k", "Annual arrest records"):
        window = element(windows, "window", **{"class": "worksheet"}, name=title)
        cards = element(window, "cards")
        edge = element(cards, "edge", name="right")
        strip = element(edge, "strip", size="200")
        element(strip, "card", **{"type": "filter", "pane-specification-id": "0"},
                column="[ice].[none:year:nk]")
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_workbook(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("ice-geography.twb", workbook_xml())
        archive.write(SOURCE, "data/arrest_rate_panel.csv")
    return output


if __name__ == "__main__":
    build_workbook(REPO / "bi/ice-geography.twbx")
