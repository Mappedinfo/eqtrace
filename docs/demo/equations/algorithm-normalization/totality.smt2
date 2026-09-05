; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(declare-fun mu () Real)
(declare-fun sigma () Real)
(declare-fun epsilon () Real)
(assert
 (<= (- 4.0) x))
(assert
 (>= 4.0 x))
(assert
 (<= (- 1.0) mu))
(assert
 (>= 1.0 mu))
(assert
 (<= (/ 1.0 10.0) sigma))
(assert
 (>= 3.0 sigma))
(assert
 (<= (/ 1.0 1000.0) epsilon))
(assert
 (>= (/ 1.0 100.0) epsilon))
(assert
 (let ((?x51 (+ sigma epsilon)))
(let (($x55 (and (distinct ?x51 0.0) true)))
(not (and $x55 $x55)))))
(check-sat)
