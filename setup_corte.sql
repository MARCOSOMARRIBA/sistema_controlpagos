CREATE OR REPLACE FUNCTION actualizar_corte_mensual_ajustador()
RETURNS TRIGGER AS $$
DECLARE
    v_mes_corte VARCHAR(7);
    v_ajustador INT;
    v_total_honorarios DECIMAL(12,2) := 0;
    v_total_anticipos DECIMAL(12,2) := 0;
    v_monto_neto DECIMAL(12,2) := 0;
BEGIN
    v_ajustador := NEW.id_ajustador;
    IF NEW.fecha_pago IS NOT NULL THEN
        v_mes_corte := to_char(NEW.fecha_pago, 'YYYY-MM');
    ELSE
        v_mes_corte := to_char(NEW.fecha_emision, 'YYYY-MM');
    END IF;

    IF v_ajustador IS NULL OR v_mes_corte IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT COALESCE(SUM(monto), 0) INTO v_total_honorarios
    FROM factura
    WHERE id_ajustador = v_ajustador 
      AND estatus_factura = 'PAGADA'
      AND to_char(COALESCE(fecha_pago, fecha_emision), 'YYYY-MM') = v_mes_corte;

    SELECT COALESCE(total_anticipos_descontados, 0) INTO v_total_anticipos
    FROM corte_mensual
    WHERE id_ajustador = v_ajustador AND mes_corte = v_mes_corte;
    
    v_monto_neto := v_total_honorarios - v_total_anticipos;

    INSERT INTO corte_mensual (id_ajustador, mes_corte, total_honorarios, total_anticipos_descontados, monto_neto_pagado)
    VALUES (v_ajustador, v_mes_corte, v_total_honorarios, v_total_anticipos, v_monto_neto)
    ON CONFLICT (id_ajustador, mes_corte)
    DO UPDATE SET 
        total_honorarios = EXCLUDED.total_honorarios,
        monto_neto_pagado = EXCLUDED.monto_neto_pagado;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_actualizar_corte_mensual ON factura CASCADE;
CREATE TRIGGER trigger_actualizar_corte_mensual
AFTER INSERT OR UPDATE ON factura
FOR EACH ROW
EXECUTE FUNCTION actualizar_corte_mensual_ajustador();
