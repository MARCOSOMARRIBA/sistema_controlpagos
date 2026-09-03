import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
# Just append the new classes to views.py
addition = """

class MisInspeccionesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsInspectorRole]

    def get(self, request):
        try:
            inspector_custom = UsuarioCustom.objects.get(username=request.user.username)
        except UsuarioCustom.DoesNotExist:
            return Response({"warning": "El usuario no tiene perfil de inspector.", "inspecciones": [], "resumen": []})

        mes_filter = request.query_params.get("mes", None)
        inspecciones_qs = Inspeccion.objects.select_related(
            "id_siniestro", "id_siniestro__aseguradora", "id_siniestro__ajustador"
        ).filter(id_siniestro__ajustador=inspector_custom)

        if mes_filter:
            try:
                anio, mes = mes_filter.split("-")
                inspecciones_qs = inspecciones_qs.filter(
                    fecha_inspeccion__year=int(anio), fecha_inspeccion__month=int(mes)
                )
            except (ValueError, AttributeError):
                pass

        inspecciones_data = []
        total_general = 0.0
        from collections import defaultdict
        resumen_mes = defaultdict(lambda: {"total": 0.0, "count": 0})

        for i in inspecciones_qs:
            s = i.id_siniestro
            aseg = s.aseguradora
            total = float(i.total_pagar or 0)
            mes_key = i.fecha_inspeccion.strftime("%Y-%m") if i.fecha_inspeccion else "Sin fecha"
            inspecciones_data.append({
                "id": i.id_inspeccion,
                "numero_siniestro": s.numero_siniestro or "",
                "asegurado": s.asegurado or "",
                "aseguradora": aseg.nombre if aseg else "",
                "solo_inspecciones": aseg.solo_inspecciones if aseg else False,
                "fecha_inspeccion": i.fecha_inspeccion.strftime("%Y-%m-%d") if i.fecha_inspeccion else None,
                "km_recorridos": float(i.km_recorridos or 0),
                "costo": float(i.costo or 0),
                "viaticos": float(i.viaticos or 0),
                "peajes": float(i.peajes or 0),
                "total_pagar": total,
                "mes": mes_key,
            })
            total_general += total
            resumen_mes[mes_key]["total"] += total
            resumen_mes[mes_key]["count"] += 1

        resumen = [
            {"mes": m, "total": round(v["total"], 2), "num_inspecciones": v["count"]}
            for m, v in sorted(resumen_mes.items(), reverse=True)
        ]
        return Response({"inspecciones": inspecciones_data, "resumen": resumen, "total_general": round(total_general, 2)})


class InspectoresListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        inspectores = UsuarioCustom.objects.filter(rol="INSPECTOR").values_list("username", flat=True)
        return Response(list(inspectores))
"""

with open("siniestros/views.py", "a") as f:
    f.write(addition)

print("views.py actualizado OK")
